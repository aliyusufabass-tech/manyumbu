import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .messaging_services import create_message, delivery_ack, mark_read, message_payload, presence_payload, update_presence
from .models import Conversation, ConversationParticipant, Message, UserPresence, WebSocketSession


class EnvelopeConsumer(AsyncJsonWebsocketConsumer):
    event_version = 1

    async def send_event(self, event, data=None, request_id=None):
        await self.send_json({"event": event, "version": self.event_version, "data": data or {}, "request_id": request_id})

    async def reject_anonymous(self):
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return True
        return False

    async def relay_event(self, event):
        await self.send_json(event["payload"])


class ChatConsumer(EnvelopeConsumer):
    async def connect(self):
        if await self.reject_anonymous():
            return
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        allowed = await self.is_member()
        if not allowed:
            await self.close(code=4403)
            return
        self.group_name = f"conversation.{self.conversation_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.record_session(True)
        await self.send_event("connection.ready", {"conversation_id": str(self.conversation_id)})

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self.record_session(False)

    async def receive_json(self, content, **kwargs):
        event = content.get("event")
        request_id = content.get("request_id")
        data = content.get("data", {}) or {}
        try:
            if event == "message.send":
                payload = await self.create_text_message(data)
                await self.channel_layer.group_send(self.group_name, {"type": "relay.event", "payload": {"event": "message.created", "version": self.event_version, "data": payload, "request_id": request_id}})
            elif event == "message.delivered":
                payload = await self.mark_delivered(data)
                await self.channel_layer.group_send(self.group_name, {"type": "relay.event", "payload": {"event": "message.delivered", "version": self.event_version, "data": payload, "request_id": request_id}})
            elif event == "message.read":
                payload = await self.mark_read_event(data)
                await self.channel_layer.group_send(self.group_name, {"type": "relay.event", "payload": {"event": "message.read", "version": self.event_version, "data": payload, "request_id": request_id}})
            elif event in {"typing.start", "typing.stop", "recording.start", "recording.stop"}:
                await self.channel_layer.group_send(self.group_name, {"type": "relay.event", "payload": {"event": event.replace("start", "updated").replace("stop", "updated"), "version": self.event_version, "data": {"username": self.scope["user"].username, "active": event.endswith("start")}, "request_id": request_id}})
            elif event == "presence.heartbeat":
                await self.heartbeat()
                await self.send_event("message.acknowledged", {"ok": True}, request_id)
            else:
                await self.send_event("error", {"message": "Unknown event."}, request_id)
        except Exception as exc:
            await self.send_event("error", {"message": str(exc)}, request_id)

    @database_sync_to_async
    def is_member(self):
        return ConversationParticipant.objects.filter(conversation_id=self.conversation_id, user=self.scope["user"]).exists()

    @database_sync_to_async
    def record_session(self, connected):
        if connected:
            WebSocketSession.objects.create(user=self.scope["user"], channel_name=self.channel_name, device_id=self.scope.get("query_string", b"").decode()[:120])
            update_presence(self.scope["user"], UserPresence.STATE_ONLINE)
        else:
            WebSocketSession.objects.filter(channel_name=self.channel_name, disconnected_at__isnull=True).update(disconnected_at=__import__("django.utils.timezone").utils.timezone.now())
            if not WebSocketSession.objects.filter(user=self.scope["user"], disconnected_at__isnull=True).exists():
                update_presence(self.scope["user"], UserPresence.STATE_RECENTLY_ACTIVE)

    @database_sync_to_async
    def create_text_message(self, data):
        conversation = Conversation.objects.get(id=self.conversation_id)
        message, _ = create_message(self.scope["user"], conversation, {"message_type": data.get("message_type", "text"), "text": data.get("text", ""), "client_message_id": data.get("client_message_id", ""), "reply_to_id": data.get("reply_to_id")}, [])
        return {"message": message_payload(message, self.scope["user"])}

    @database_sync_to_async
    def mark_delivered(self, data):
        message = Message.objects.get(id=data["message_id"], conversation_id=self.conversation_id)
        delivery_ack(message, self.scope["user"], data.get("device_id", "websocket"))
        return {"message_id": str(message.id), "username": self.scope["user"].username}

    @database_sync_to_async
    def mark_read_event(self, data):
        conversation = Conversation.objects.get(id=self.conversation_id)
        message = Message.objects.filter(id=data.get("message_id"), conversation=conversation).first()
        mark_read(conversation, self.scope["user"], message)
        return {"conversation_id": self.conversation_id, "username": self.scope["user"].username}

    @database_sync_to_async
    def heartbeat(self):
        update_presence(self.scope["user"], UserPresence.STATE_ONLINE)


class PresenceConsumer(EnvelopeConsumer):
    async def connect(self):
        if await self.reject_anonymous():
            return
        self.group_name = f"presence.{self.scope['user'].phone_number}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.set_online()
        await self.send_event("presence.updated", {"state": "online"})

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self.set_recently_active()

    async def receive_json(self, content, **kwargs):
        if content.get("event") == "presence.heartbeat":
            await self.set_online()
            await self.send_event("presence.updated", {"state": "online"}, content.get("request_id"))
        else:
            await self.send_event("error", {"message": "Unknown event."}, content.get("request_id"))

    @database_sync_to_async
    def set_online(self):
        update_presence(self.scope["user"], UserPresence.STATE_ONLINE)

    @database_sync_to_async
    def set_recently_active(self):
        update_presence(self.scope["user"], UserPresence.STATE_RECENTLY_ACTIVE)


class NotificationsConsumer(EnvelopeConsumer):
    async def connect(self):
        if await self.reject_anonymous():
            return
        self.group_name = f"notifications.{self.scope['user'].phone_number}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_event("connection.ready", {"stream": "notifications"})

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

