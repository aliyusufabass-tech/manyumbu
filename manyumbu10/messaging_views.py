import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .messaging_services import (
    MAX_PINS_PER_CONVERSATION,
    conversation_payload,
    create_message,
    delete_for_everyone,
    delivery_ack,
    edit_message,
    get_or_create_private_conversation,
    mark_read,
    message_payload,
    message_queryset_for,
    presence_payload,
    report_context,
)
from .models import (
    AdminAuditLog,
    Conversation,
    ConversationArchive,
    ConversationClearState,
    ConversationMute,
    ConversationParticipant,
    Message,
    MessageAttachment,
    MessageDeletion,
    MessagePin,
    MessageReaction,
    MessageReport,
    MessageRequest,
    MessageStar,
    ConversationReport,
    Post,
    Reel,
    Story,
    UserDevice,
)
from .post_services import can_access_post
from .phase4_services import can_access_reel, can_access_story
from .profile_views import AuthenticatedView, compact_user, get_target, page
from .views import body, response


def parse_payload(request):
    if request.content_type and request.content_type.startswith("multipart/"):
        payload = request.POST.dict()
        for key in ["shared_content", "location", "contact", "forwarded_from", "waveform"]:
            if key in payload:
                try:
                    payload[key] = json.loads(payload[key])
                except Exception:
                    payload[key] = {} if key != "waveform" else []
        return payload
    return body(request)


def get_conversation_or_404(user, conversation_id):
    conversation = Conversation.objects.prefetch_related("participants__user").get(id=conversation_id)
    if not ConversationParticipant.objects.filter(conversation=conversation, user=user).exists():
        raise PermissionError("You are not a participant in this conversation.")
    return conversation


@method_decorator(csrf_exempt, name="dispatch")
class ConversationListView(AuthenticatedView):
    def get(self, request):
        qs = Conversation.objects.filter(participants__user=request.user_obj, participants__deleted_at__isnull=True).select_related("last_message", "last_message__sender").prefetch_related("participants__user").distinct()
        if request.GET.get("archived") != "1":
            qs = qs.filter(participants__user=request.user_obj, participants__archived_at__isnull=True)
        q = request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(participants__user__username__icontains=q) | Q(participants__user__full_name__icontains=q)).exclude(participants__user=request.user_obj).distinct()
        cursor = request.GET.get("cursor")
        if cursor:
            parsed = parse_datetime(cursor.replace(" ", "+")) or parse_datetime(cursor)
            if parsed:
                qs = qs.filter(updated_at__lt=parsed)
        limit = min(max(int(request.GET.get("limit", 20)), 1), 50)
        rows = list(qs.order_by("-last_message_at", "-updated_at")[: limit + 1])
        next_cursor = rows[-1].updated_at.isoformat() if len(rows) > limit else None
        rows = rows[:limit]
        return response(True, "Conversations loaded.", {"results": [conversation_payload(item, request.user_obj) for item in rows], "next_cursor": next_cursor})

    def post(self, request):
        try:
            payload = body(request)
            target = get_target(payload.get("username") or payload.get("target") or "")
            conversation, created, request_required = get_or_create_private_conversation(request.user_obj, target, payload.get("initial_text", ""))
            if payload.get("initial_text") or payload.get("message_type") or request.FILES:
                message_payload_in = {"text": payload.get("initial_text", ""), "message_type": payload.get("message_type", Message.TYPE_TEXT), "client_message_id": payload.get("client_message_id", "")}
                create_message(request.user_obj, conversation, message_payload_in, [])
            return response(True, "Conversation ready.", {"conversation": conversation_payload(conversation, request.user_obj), "created": created, "message_request_required": request_required}, status=201 if created else 200)
        except get_user_model().DoesNotExist:
            return response(False, "User was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)
        except (ValueError, IntegrityError) as exc:
            return response(False, str(exc), status=400)


@method_decorator(csrf_exempt, name="dispatch")
class ConversationDetailView(AuthenticatedView):
    def get(self, request, conversation_id):
        try:
            conversation = get_conversation_or_404(request.user_obj, conversation_id)
            peer = conversation.participants.exclude(user=request.user_obj).select_related("user").first()
            data = conversation_payload(conversation, request.user_obj)
            data["presence"] = presence_payload(peer.user, request.user_obj) if peer else {"state": "offline", "last_seen_at": None}
            return response(True, "Conversation loaded.", {"conversation": data})
        except Conversation.DoesNotExist:
            return response(False, "Conversation was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)

    def patch(self, request, conversation_id):
        try:
            conversation = get_conversation_or_404(request.user_obj, conversation_id)
            participant = ConversationParticipant.objects.get(conversation=conversation, user=request.user_obj)
            payload = body(request)
            if "notification_preference" in payload:
                participant.notification_preference = payload["notification_preference"]
            if "keep_archived" in payload:
                participant.keep_archived = bool(payload["keep_archived"])
            participant.save()
            return response(True, "Conversation settings updated.", {"conversation": conversation_payload(conversation, request.user_obj)})
        except Conversation.DoesNotExist:
            return response(False, "Conversation was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)


@method_decorator(csrf_exempt, name="dispatch")
class ConversationStateView(AuthenticatedView):
    def post(self, request, conversation_id, action):
        try:
            conversation = get_conversation_or_404(request.user_obj, conversation_id)
            participant = ConversationParticipant.objects.get(conversation=conversation, user=request.user_obj)
            payload = body(request)
            now = timezone.now()
            if action == "read":
                mark_read(conversation, request.user_obj)
            elif action == "unread":
                participant.marked_unread = True
                participant.save(update_fields=["marked_unread", "updated_at"])
            elif action == "archive":
                participant.archived_at = now
                participant.save(update_fields=["archived_at", "updated_at"])
                ConversationArchive.objects.get_or_create(conversation=conversation, user=request.user_obj)
            elif action == "unarchive":
                participant.archived_at = None
                participant.save(update_fields=["archived_at", "updated_at"])
                ConversationArchive.objects.filter(conversation=conversation, user=request.user_obj).delete()
            elif action == "mute":
                duration = payload.get("duration", "8h")
                choices = {"1h": timedelta(hours=1), "8h": timedelta(hours=8), "1d": timedelta(days=1), "1w": timedelta(days=7), "forever": None}
                if duration not in choices:
                    return response(False, "Unknown mute duration.", status=400)
                until = None if choices[duration] is None else now + choices[duration]
                participant.muted_until = until
                participant.save(update_fields=["muted_until", "updated_at"])
                ConversationMute.objects.update_or_create(conversation=conversation, user=request.user_obj, defaults={"muted_until": until})
            elif action == "clear":
                participant.cleared_before = now
                participant.save(update_fields=["cleared_before", "updated_at"])
                ConversationClearState.objects.update_or_create(conversation=conversation, user=request.user_obj, defaults={"cleared_before": now})
            elif action == "report":
                report, _ = ConversationReport.objects.get_or_create(conversation=conversation, reporter=request.user_obj, reason=payload.get("reason", "other"), defaults={"details": payload.get("details", "")[:1000], "context_snapshot": report_context(conversation=conversation)})
                return response(True, "Conversation report submitted.", {"report_id": report.id})
            else:
                return response(False, "Unknown conversation action.", status=400)
            return response(True, "Conversation updated.", {"conversation": conversation_payload(conversation, request.user_obj)})
        except Conversation.DoesNotExist:
            return response(False, "Conversation was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)

    def delete(self, request, conversation_id, action):
        if action != "mute":
            return response(False, "Unknown conversation action.", status=400)
        try:
            conversation = get_conversation_or_404(request.user_obj, conversation_id)
            participant = ConversationParticipant.objects.get(conversation=conversation, user=request.user_obj)
            participant.muted_until = None
            participant.save(update_fields=["muted_until", "updated_at"])
            ConversationMute.objects.filter(conversation=conversation, user=request.user_obj).delete()
            return response(True, "Conversation unmuted.", {"conversation": conversation_payload(conversation, request.user_obj)})
        except Conversation.DoesNotExist:
            return response(False, "Conversation was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)


@method_decorator(csrf_exempt, name="dispatch")
class ConversationMessagesView(AuthenticatedView):
    def get(self, request, conversation_id):
        try:
            conversation = get_conversation_or_404(request.user_obj, conversation_id)
            qs = message_queryset_for(request.user_obj, conversation).order_by("-created_at")
            before = request.GET.get("before")
            after = request.GET.get("after")
            if before:
                parsed = parse_datetime(before.replace(" ", "+")) or parse_datetime(before)
                if parsed:
                    qs = qs.filter(created_at__lt=parsed)
            if after:
                parsed = parse_datetime(after.replace(" ", "+")) or parse_datetime(after)
                if parsed:
                    qs = qs.filter(created_at__gt=parsed).order_by("created_at")
            limit = min(max(int(request.GET.get("limit", 30)), 1), 100)
            rows = list(qs[: limit + 1])
            next_cursor = rows[-1].created_at.isoformat() if len(rows) > limit else None
            rows = rows[:limit]
            return response(True, "Messages loaded.", {"results": [message_payload(item, request.user_obj) for item in rows], "next_cursor": next_cursor})
        except Conversation.DoesNotExist:
            return response(False, "Conversation was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)

    def post(self, request, conversation_id):
        try:
            conversation = get_conversation_or_404(request.user_obj, conversation_id)
            payload = parse_payload(request)
            msg, created = create_message(request.user_obj, conversation, payload, request.FILES.getlist("attachments") or request.FILES.getlist("attachment"))
            return response(True, "Message sent successfully.", {"message": message_payload(msg, request.user_obj), "deduplicated": not created}, status=201 if created else 200)
        except (Conversation.DoesNotExist, Message.DoesNotExist):
            return response(False, "Conversation or reply message was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)
        except (ValueError, IntegrityError) as exc:
            return response(False, str(exc), status=400)


@method_decorator(csrf_exempt, name="dispatch")
class MessageDetailView(AuthenticatedView):
    def get(self, request, message_id):
        try:
            msg = Message.objects.select_related("conversation", "sender", "reply_to", "reply_to__sender").prefetch_related("attachments", "reactions__user").get(id=message_id)
            get_conversation_or_404(request.user_obj, msg.conversation_id)
            return response(True, "Message loaded.", {"message": message_payload(msg, request.user_obj)})
        except Message.DoesNotExist:
            return response(False, "Message was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)

    def patch(self, request, message_id):
        try:
            msg = Message.objects.get(id=message_id)
            get_conversation_or_404(request.user_obj, msg.conversation_id)
            msg = edit_message(msg, request.user_obj, body(request).get("text", ""))
            return response(True, "Message updated.", {"message": message_payload(msg, request.user_obj)})
        except Message.DoesNotExist:
            return response(False, "Message was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)
        except ValueError as exc:
            return response(False, str(exc), status=400)


@method_decorator(csrf_exempt, name="dispatch")
class MessageDeleteForMeView(AuthenticatedView):
    def delete(self, request, message_id):
        try:
            msg = Message.objects.get(id=message_id)
            get_conversation_or_404(request.user_obj, msg.conversation_id)
            MessageDeletion.objects.get_or_create(message=msg, user=request.user_obj)
            return response(True, "Message deleted for you.")
        except Message.DoesNotExist:
            return response(False, "Message was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)


@method_decorator(csrf_exempt, name="dispatch")
class MessageDeleteForEveryoneView(AuthenticatedView):
    def delete(self, request, message_id):
        try:
            msg = Message.objects.get(id=message_id)
            get_conversation_or_404(request.user_obj, msg.conversation_id)
            delete_for_everyone(msg, request.user_obj)
            return response(True, "Message deleted for everyone.", {"message": message_payload(msg, request.user_obj)})
        except Message.DoesNotExist:
            return response(False, "Message was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)


@method_decorator(csrf_exempt, name="dispatch")
class MessageActionView(AuthenticatedView):
    def post(self, request, message_id, action):
        try:
            msg = Message.objects.select_related("conversation", "sender").get(id=message_id)
            get_conversation_or_404(request.user_obj, msg.conversation_id)
            payload = body(request)
            if action == "react":
                reaction = payload.get("reaction", "like")
                if reaction not in {key for key, _ in MessageReaction.REACTIONS}:
                    return response(False, "Unknown reaction.", status=400)
                MessageReaction.objects.update_or_create(message=msg, user=request.user_obj, defaults={"reaction": reaction})
            elif action == "star":
                MessageStar.objects.get_or_create(message=msg, user=request.user_obj)
            elif action == "pin":
                if MessagePin.objects.filter(conversation=msg.conversation).count() >= MAX_PINS_PER_CONVERSATION and not MessagePin.objects.filter(conversation=msg.conversation, message=msg).exists():
                    return response(False, "Pinned message limit reached.", status=400)
                MessagePin.objects.get_or_create(message=msg, conversation=msg.conversation, defaults={"pinned_by": request.user_obj})
            elif action == "forward":
                target = get_target(payload.get("username") or payload.get("target") or "")
                target_convo, _, _ = get_or_create_private_conversation(request.user_obj, target, msg.text)
                forwarded, _ = create_message(request.user_obj, target_convo, {"message_type": msg.message_type, "text": payload.get("note", msg.text), "is_forwarded": True, "forwarded_from": {"message_id": str(msg.id)}, "shared_content": msg.shared_content}, [])
                return response(True, "Message forwarded.", {"message": message_payload(forwarded, request.user_obj), "conversation": conversation_payload(target_convo, request.user_obj)}, status=201)
            elif action == "report":
                report, _ = MessageReport.objects.get_or_create(message=msg, reporter=request.user_obj, reason=payload.get("reason", "other"), defaults={"details": payload.get("details", "")[:1000], "context_snapshot": report_context(message=msg)})
                return response(True, "Message report submitted.", {"report_id": report.id})
            elif action == "delivered":
                delivery_ack(msg, request.user_obj, payload.get("device_id", ""))
            elif action == "read":
                mark_read(msg.conversation, request.user_obj, msg)
            else:
                return response(False, "Unknown message action.", status=400)
            return response(True, "Message action completed.", {"message": message_payload(msg, request.user_obj)})
        except (Message.DoesNotExist, get_user_model().DoesNotExist):
            return response(False, "Message or user was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)
        except ValueError as exc:
            return response(False, str(exc), status=400)

    def delete(self, request, message_id, action):
        try:
            msg = Message.objects.get(id=message_id)
            get_conversation_or_404(request.user_obj, msg.conversation_id)
            if action == "react":
                MessageReaction.objects.filter(message=msg, user=request.user_obj).delete()
            elif action == "star":
                MessageStar.objects.filter(message=msg, user=request.user_obj).delete()
            elif action == "pin":
                MessagePin.objects.filter(message=msg, conversation=msg.conversation).delete()
            else:
                return response(False, "Unknown message action.", status=400)
            return response(True, "Message action removed.", {"message": message_payload(msg, request.user_obj)})
        except Message.DoesNotExist:
            return response(False, "Message was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)


@method_decorator(csrf_exempt, name="dispatch")
class MessageSearchView(AuthenticatedView):
    def get(self, request, conversation_id):
        try:
            conversation = get_conversation_or_404(request.user_obj, conversation_id)
            q = request.GET.get("q", "").strip()
            qs = message_queryset_for(request.user_obj, conversation).order_by("-created_at")
            if q:
                qs = qs.filter(Q(text__icontains=q) | Q(attachments__file_name__icontains=q)).distinct()
            return response(True, "Message search loaded.", page(request, qs, lambda item: message_payload(item, request.user_obj)))
        except Conversation.DoesNotExist:
            return response(False, "Conversation was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)


@method_decorator(csrf_exempt, name="dispatch")
class SharedMediaView(AuthenticatedView):
    def get(self, request, conversation_id):
        try:
            conversation = get_conversation_or_404(request.user_obj, conversation_id)
            messages = message_queryset_for(request.user_obj, conversation).values_list("id", flat=True)
            kind = request.GET.get("kind")
            qs = MessageAttachment.objects.filter(message_id__in=messages).select_related("message", "message__sender").order_by("-created_at")
            if kind:
                qs = qs.filter(kind=kind)
            return response(True, "Shared media loaded.", page(request, qs, lambda item: {"message_id": str(item.message_id), "sender": compact_user(item.message.sender, request.user_obj), "attachment": {"id": str(item.id), "kind": item.kind, "file_name": item.file_name, "url": item.file.url if item.file else "", "file_size": item.file_size, "created_at": item.created_at.isoformat()}}))
        except Conversation.DoesNotExist:
            return response(False, "Conversation was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)


@method_decorator(csrf_exempt, name="dispatch")
class MessageRequestListView(AuthenticatedView):
    def get(self, request):
        qs = MessageRequest.objects.filter(receiver=request.user_obj, status=MessageRequest.STATUS_PENDING).select_related("sender", "conversation").order_by("-created_at")
        return response(True, "Message requests loaded.", page(request, qs, lambda req: {"id": str(req.id), "conversation_id": str(req.conversation_id), "sender": compact_user(req.sender, request.user_obj), "preview_text": req.preview_text, "status": req.status, "created_at": req.created_at.isoformat()}))


@method_decorator(csrf_exempt, name="dispatch")
class MessageRequestActionView(AuthenticatedView):
    def post(self, request, request_id, action):
        try:
            req = MessageRequest.objects.select_related("conversation", "sender", "receiver").get(id=request_id, receiver=request.user_obj)
            now = timezone.now()
            if action == "accept":
                req.status = MessageRequest.STATUS_ACCEPTED
                ConversationParticipant.objects.filter(conversation=req.conversation).update(request_state=ConversationParticipant.REQUEST_ACCEPTED, updated_at=now)
            elif action == "reject":
                req.status = MessageRequest.STATUS_REJECTED
                ConversationParticipant.objects.filter(conversation=req.conversation, user=request.user_obj).update(request_state=ConversationParticipant.REQUEST_REJECTED, updated_at=now)
            elif action == "spam":
                req.status = MessageRequest.STATUS_SPAM
                req.spam_score += 1
                ConversationParticipant.objects.filter(conversation=req.conversation, user=request.user_obj).update(request_state=ConversationParticipant.REQUEST_SPAM, updated_at=now)
            else:
                return response(False, "Unknown message request action.", status=400)
            req.responded_at = now
            req.save(update_fields=["status", "responded_at", "spam_score", "updated_at"])
            return response(True, "Message request updated.", {"request_id": str(req.id), "status": req.status})
        except MessageRequest.DoesNotExist:
            return response(False, "Message request was not found.", status=404)

    def delete(self, request, request_id, action=None):
        try:
            req = MessageRequest.objects.get(id=request_id, receiver=request.user_obj)
            req.status = MessageRequest.STATUS_DELETED
            req.responded_at = timezone.now()
            req.save(update_fields=["status", "responded_at", "updated_at"])
            ConversationParticipant.objects.filter(conversation=req.conversation, user=request.user_obj).update(request_state=ConversationParticipant.REQUEST_DELETED)
            return response(True, "Message request deleted.")
        except MessageRequest.DoesNotExist:
            return response(False, "Message request was not found.", status=404)


@method_decorator(csrf_exempt, name="dispatch")
class MessagingSyncView(AuthenticatedView):
    def get(self, request, kind):
        cursor = request.GET.get("cursor")
        parsed = parse_datetime(cursor.replace(" ", "+")) if cursor else None
        if kind == "conversations":
            qs = Conversation.objects.filter(participants__user=request.user_obj).distinct().order_by("updated_at")
            if parsed:
                qs = qs.filter(updated_at__gt=parsed)
            return response(True, "Conversation sync loaded.", {"results": [conversation_payload(item, request.user_obj) for item in qs[:50]], "next_cursor": timezone.now().isoformat()})
        if kind == "messages":
            qs = Message.objects.filter(conversation__participants__user=request.user_obj).select_related("conversation", "sender").order_by("created_at")
            if parsed:
                qs = qs.filter(updated_at__gt=parsed)
            return response(True, "Message sync loaded.", {"results": [message_payload(item, request.user_obj) for item in qs[:100]], "next_cursor": timezone.now().isoformat()})
        return response(False, "Unknown sync type.", status=404)


@method_decorator(csrf_exempt, name="dispatch")
class DeviceView(AuthenticatedView):
    def post(self, request):
        payload = body(request)
        device, _ = UserDevice.objects.update_or_create(user=request.user_obj, device_id=payload.get("device_id", "default")[:120], defaults={"device_name": payload.get("device_name", "")[:120], "platform": payload.get("platform", "")[:40], "push_token": payload.get("push_token", "")[:255], "notification_preferences": payload.get("notification_preferences", {}), "last_seen_at": timezone.now(), "revoked_at": None})
        return response(True, "Device registered.", {"device_id": device.device_id})

    def delete(self, request):
        payload = body(request)
        UserDevice.objects.filter(user=request.user_obj, device_id=payload.get("device_id", "default")[:120]).update(revoked_at=timezone.now())
        return response(True, "Device removed.")


@method_decorator(csrf_exempt, name="dispatch")
class AdminMessageReportView(AuthenticatedView):
    def _staff(self, request):
        if not request.user_obj.is_staff:
            raise PermissionError("Staff access is required.")

    def get(self, request):
        try:
            self._staff(request)
            kind = request.GET.get("kind", "messages")
            status_filter = request.GET.get("status")
            if kind == "conversations":
                qs = ConversationReport.objects.select_related("reporter", "conversation").order_by("-created_at")
                if status_filter:
                    qs = qs.filter(status=status_filter)
                return response(True, "Conversation reports loaded.", page(request, qs, lambda item: {"id": item.id, "kind": "conversation", "conversation_id": str(item.conversation_id), "reporter": compact_user(item.reporter, request.user_obj), "reason": item.reason, "details": item.details, "status": item.status, "context_snapshot": item.context_snapshot, "created_at": item.created_at.isoformat()}))
            qs = MessageReport.objects.select_related("reporter", "message", "message__sender").order_by("-created_at")
            if status_filter:
                qs = qs.filter(status=status_filter)
            return response(True, "Message reports loaded.", page(request, qs, lambda item: {"id": item.id, "kind": "message", "message_id": str(item.message_id), "message_sender": compact_user(item.message.sender, request.user_obj), "reporter": compact_user(item.reporter, request.user_obj), "reason": item.reason, "details": item.details, "status": item.status, "context_snapshot": item.context_snapshot, "created_at": item.created_at.isoformat()}))
        except PermissionError as exc:
            return response(False, str(exc), status=403)

    def post(self, request, report_kind, report_id, action):
        try:
            self._staff(request)
            payload = body(request)
            model = MessageReport if report_kind == "messages" else ConversationReport
            report = model.objects.get(id=report_id)
            mapping = {"pending": "pending", "review": "under_review", "resolve": "resolved", "reject": "rejected"}
            if action not in mapping:
                return response(False, "Unknown moderation action.", status=400)
            report.status = mapping[action]
            report.save(update_fields=["status", "updated_at"])
            AdminAuditLog.objects.create(admin_user=request.user_obj, action=f"{report_kind}_report_{action}", target=str(report_id), reason=payload.get("reason", ""))
            return response(True, "Report moderation updated.", {"status": report.status})
        except PermissionError as exc:
            return response(False, str(exc), status=403)
        except (MessageReport.DoesNotExist, ConversationReport.DoesNotExist):
            return response(False, "Report was not found.", status=404)
