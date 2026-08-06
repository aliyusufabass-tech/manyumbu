import html
import mimetypes
import os
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import (
    Conversation,
    ConversationClearState,
    ConversationParticipant,
    Follow,
    Message,
    MessageAttachment,
    MessageDeliveryReceipt,
    MessagePin,
    MessageReaction,
    MessageReadReceipt,
    MessageReport,
    MessageRequest,
    MessageStar,
    Notification,
    UserPresence,
)
from .profile_views import compact_user
from .storage import absolute_media_url
from .services import ensure_profile_records, users_blocked_between

MAX_TEXT_LENGTH = 5000
MAX_ATTACHMENTS = 10
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_VIDEO_SIZE = 100 * 1024 * 1024
MAX_AUDIO_SIZE = 25 * 1024 * 1024
MAX_DOCUMENT_SIZE = 25 * 1024 * 1024
MAX_VOICE_NOTE_SECONDS = 15 * 60
EDIT_WINDOW = timedelta(minutes=15)
DELETE_FOR_EVERYONE_WINDOW = timedelta(hours=24)
MAX_PINS_PER_CONVERSATION = 5

IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
VIDEO_MIMES = {"video/mp4", "video/quicktime", "video/webm"}
AUDIO_MIMES = {"audio/mpeg", "audio/mp4", "audio/wav", "audio/webm", "audio/aac", "audio/ogg"}
DOCUMENT_MIMES = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "text/plain"}
DANGEROUS_EXTENSIONS = {".exe", ".bat", ".cmd", ".com", ".scr", ".js", ".vbs", ".ps1", ".sh", ".dll", ".msi"}


def private_pair_key(a, b):
    first, second = sorted([a.phone_number, b.phone_number])
    return f"{first}:{second}"


def other_participant(conversation, user):
    return get_user_model().objects.filter(conversation_participations__conversation=conversation).exclude(phone_number=user.phone_number).first()


def participant_for(conversation, user):
    return ConversationParticipant.objects.filter(conversation=conversation, user=user).first()


def ensure_membership(conversation, user):
    participant = participant_for(conversation, user)
    if not participant:
        raise PermissionError("You are not a participant in this conversation.")
    if participant.deleted_at:
        participant.deleted_at = None
        participant.save(update_fields=["deleted_at", "updated_at"])
    return participant


def clean_message_text(value, required_for_text=True):
    text = str(value or "").replace("\x00", "").strip()
    text = "\n".join(line.rstrip() for line in text.splitlines())
    if required_for_text and not text:
        raise ValueError("Message text is required.")
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(f"Message text must be {MAX_TEXT_LENGTH} characters or fewer.")
    return html.escape(text, quote=False)


def is_mutual_follow(a, b):
    return Follow.objects.filter(follower=a, following=b).exists() and Follow.objects.filter(follower=b, following=a).exists()


def follows(a, b):
    return Follow.objects.filter(follower=a, following=b).exists()


def messaging_privacy_allows(sender, receiver):
    if sender == receiver:
        raise ValueError("You cannot start a conversation with yourself.")
    ensure_profile_records(sender)
    ensure_profile_records(receiver)
    if not receiver.is_active or not receiver.is_email_verified:
        raise PermissionError("This user cannot receive messages.")
    if users_blocked_between(sender, receiver):
        raise PermissionError("Messaging is blocked between these users.")
    setting = receiver.privacy_settings.who_can_message_me
    if setting == "no_one":
        return False, False
    if setting == "mutual_followers":
        allowed = is_mutual_follow(sender, receiver)
    elif setting == "people_i_follow":
        allowed = follows(receiver, sender)
    else:
        allowed = True
    if allowed:
        return True, False
    if receiver.privacy_settings.allow_message_requests:
        return True, True
    return False, False


@transaction.atomic
def get_or_create_private_conversation(actor, target, initial_text=""):
    allowed, requires_request = messaging_privacy_allows(actor, target)
    if not allowed:
        raise PermissionError("This user does not allow messages from you.")
    key = private_pair_key(actor, target)
    conversation, created = Conversation.objects.select_for_update().get_or_create(private_pair_key=key, defaults={"conversation_type": Conversation.TYPE_PRIVATE, "status": Conversation.STATUS_ACTIVE})
    for user in [actor, target]:
        state = ConversationParticipant.REQUEST_NONE
        if requires_request:
            state = ConversationParticipant.REQUEST_PENDING if user == target else ConversationParticipant.REQUEST_ACCEPTED
        ConversationParticipant.objects.get_or_create(conversation=conversation, user=user, defaults={"request_state": state})
    if requires_request:
        existing_request = MessageRequest.objects.filter(conversation=conversation).first()
        if existing_request and existing_request.status == MessageRequest.STATUS_ACCEPTED:
            ConversationParticipant.objects.filter(conversation=conversation).update(request_state=ConversationParticipant.REQUEST_ACCEPTED)
            return conversation, created, False
        if existing_request and existing_request.status in {MessageRequest.STATUS_REJECTED, MessageRequest.STATUS_DELETED, MessageRequest.STATUS_SPAM}:
            raise PermissionError("This message request is no longer active.")
        MessageRequest.objects.get_or_create(conversation=conversation, sender=actor, receiver=target, status=MessageRequest.STATUS_PENDING, defaults={"preview_text": clean_message_text(initial_text, required_for_text=False)[:280]})
        ConversationParticipant.objects.filter(conversation=conversation, user=target).update(request_state=ConversationParticipant.REQUEST_PENDING)
    return conversation, created, requires_request


def can_exchange_messages(conversation, sender):
    ensure_membership(conversation, sender)
    other = other_participant(conversation, sender)
    if not other or users_blocked_between(sender, other):
        raise PermissionError("Messaging is blocked between these users.")
    if hasattr(conversation, "message_request") and conversation.message_request.status != MessageRequest.STATUS_ACCEPTED:
        if conversation.message_request.status != MessageRequest.STATUS_PENDING or conversation.message_request.sender_id != sender.phone_number:
            raise PermissionError("Accept the message request before replying.")
    return other


def safe_filename(upload):
    name = os.path.basename(upload.name or "attachment")[:180]
    return "".join(ch for ch in name if ch.isalnum() or ch in " ._-()").strip() or "attachment"


def validate_attachment(upload, kind, duration=None, width=None, height=None):
    filename = safe_filename(upload)
    ext = os.path.splitext(filename.lower())[1]
    if ext in DANGEROUS_EXTENSIONS:
        raise ValueError("This file type is not allowed.")
    mime = getattr(upload, "content_type", "") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    size = getattr(upload, "size", 0) or 0
    if kind == MessageAttachment.KIND_IMAGE:
        if mime not in IMAGE_MIMES or size > MAX_IMAGE_SIZE:
            raise ValueError("Image attachments must be JPEG, PNG, WebP, or GIF and 10MB or smaller.")
    elif kind == MessageAttachment.KIND_VIDEO:
        if mime not in VIDEO_MIMES or size > MAX_VIDEO_SIZE:
            raise ValueError("Video attachments must be MP4, MOV, or WebM and 100MB or smaller.")
    elif kind in {MessageAttachment.KIND_AUDIO, MessageAttachment.KIND_VOICE_NOTE}:
        if mime not in AUDIO_MIMES or size > MAX_AUDIO_SIZE:
            raise ValueError("Audio attachments must use a supported audio MIME type and be 25MB or smaller.")
        if kind == MessageAttachment.KIND_VOICE_NOTE and duration and float(duration) > MAX_VOICE_NOTE_SECONDS:
            raise ValueError("Voice notes must be 15 minutes or shorter.")
    elif kind == MessageAttachment.KIND_DOCUMENT:
        if mime not in DOCUMENT_MIMES or size > MAX_DOCUMENT_SIZE:
            raise ValueError("Document attachments must be PDF, DOCX, XLSX, PPTX, or TXT and 25MB or smaller.")
    else:
        raise ValueError("Unknown attachment kind.")
    return filename, mime


def message_queryset_for(user, conversation):
    participant = ensure_membership(conversation, user)
    qs = Message.objects.filter(conversation=conversation).exclude(deleted_for__user=user).select_related("sender", "reply_to", "reply_to__sender").prefetch_related("attachments", "reactions__user")
    if participant.cleared_before:
        qs = qs.filter(created_at__gt=participant.cleared_before)
    return qs


@transaction.atomic
def create_message(sender, conversation, payload, files=None):
    other = can_exchange_messages(conversation, sender)
    message_type = payload.get("message_type", Message.TYPE_TEXT)
    files = files or []
    if len(files) > MAX_ATTACHMENTS:
        raise ValueError(f"Messages can include at most {MAX_ATTACHMENTS} attachments.")
    text_required = message_type == Message.TYPE_TEXT and not files and not payload.get("shared_content") and not payload.get("location") and not payload.get("contact")
    text = clean_message_text(payload.get("text", ""), required_for_text=text_required)
    client_id = str(payload.get("client_message_id", ""))[:80]
    if client_id:
        existing = Message.objects.filter(sender=sender, client_message_id=client_id).first()
        if existing:
            return existing, False
    reply_to = None
    if payload.get("reply_to_id"):
        reply_to = Message.objects.get(id=payload["reply_to_id"], conversation=conversation)
    message = Message.objects.create(conversation=conversation, sender=sender, message_type=message_type, text=text, reply_to=reply_to, client_message_id=client_id, shared_content=payload.get("shared_content", {}), location_payload=payload.get("location", {}), contact_payload=payload.get("contact", {}), is_forwarded=bool(payload.get("is_forwarded")), forwarded_from=payload.get("forwarded_from", {}))
    for upload in files:
        kind = payload.get("attachment_kind") or message_type
        filename, mime = validate_attachment(upload, kind, payload.get("duration"), payload.get("width"), payload.get("height"))
        MessageAttachment.objects.create(message=message, owner=sender, file=upload, kind=kind, file_name=filename, mime_type=mime, file_size=getattr(upload, "size", 0) or 0, width=payload.get("width") or None, height=payload.get("height") or None, duration=payload.get("duration") or None, waveform=payload.get("waveform", []), processing_status=MessageAttachment.PROCESSING_PENDING if kind == MessageAttachment.KIND_VIDEO else MessageAttachment.PROCESSING_READY)
    now = timezone.now()
    conversation.last_message = message
    conversation.last_message_at = now
    conversation.save(update_fields=["last_message", "last_message_at", "updated_at"])
    ConversationParticipant.objects.filter(conversation=conversation).exclude(user=sender).update(marked_unread=True, updated_at=now)
    Notification.objects.create(recipient=other, actor=sender, notification_type="private_message", message="New private message")
    return message, True


def attachment_payload(attachment):
    url = absolute_media_url(attachment.file) or ""
    return {"id": str(attachment.id), "kind": attachment.kind, "url": url, "file_name": attachment.file_name, "mime_type": attachment.mime_type, "file_size": attachment.file_size, "width": attachment.width, "height": attachment.height, "duration": attachment.duration, "thumbnail": absolute_media_url(attachment.thumbnail), "waveform": attachment.waveform, "processing_status": attachment.processing_status, "malware_scan_status": attachment.malware_scan_status}


def message_payload(message, viewer):
    deleted = bool(message.deleted_for_everyone_at)
    reply_preview = None
    if message.reply_to_id:
        original = message.reply_to
        reply_preview = {"id": str(original.id), "sender": compact_user(original.sender, viewer), "message_type": original.message_type, "text": "Message unavailable" if original.deleted_for_everyone_at else original.text[:120], "has_attachment": original.attachments.exists()}
    other = other_participant(message.conversation, viewer)
    ensure_profile_records(viewer)
    show_receipts = bool(other and getattr(other.privacy_settings, "send_read_receipts", True) and getattr(viewer.privacy_settings, "send_read_receipts", True))
    read_by = []
    if show_receipts:
        read_by = [{"username": r.user.username, "read_at": r.read_at.isoformat()} for r in message.read_receipts.select_related("user").exclude(user=message.sender)]
    return {"id": str(message.id), "conversation_id": str(message.conversation_id), "sender": compact_user(message.sender, viewer), "message_type": message.message_type, "text": "" if deleted else message.text, "reply_to": reply_preview, "is_forwarded": message.is_forwarded, "forwarded_from": {} if deleted else message.forwarded_from, "shared_content": {} if deleted else message.shared_content, "location": {} if deleted else message.location_payload, "contact": {} if deleted else message.contact_payload, "client_message_id": message.client_message_id, "status": Message.STATUS_DELETED if deleted else message.status, "is_edited": message.is_edited, "edited_at": message.edited_at.isoformat() if message.edited_at else None, "deleted_for_everyone_at": message.deleted_for_everyone_at.isoformat() if message.deleted_for_everyone_at else None, "attachments": [] if deleted else [attachment_payload(a) for a in message.attachments.all()], "reactions": [{"username": r.user.username, "reaction": r.reaction} for r in message.reactions.select_related("user").all()], "viewer_has_starred": MessageStar.objects.filter(message=message, user=viewer).exists(), "viewer_has_pinned": MessagePin.objects.filter(message=message, conversation=message.conversation).exists(), "read_by": read_by, "delivered_count": message.delivery_receipts.exclude(user=message.sender).count(), "created_at": message.created_at.isoformat(), "updated_at": message.updated_at.isoformat()}


def conversation_payload(conversation, viewer):
    participant = ensure_membership(conversation, viewer)
    peer = other_participant(conversation, viewer)
    unread_qs = message_queryset_for(viewer, conversation).exclude(sender=viewer)
    if participant.last_read_at:
        unread_qs = unread_qs.filter(created_at__gt=participant.last_read_at)
    unread_count = unread_qs.count() + (1 if participant.marked_unread and not unread_qs.exists() else 0)
    return {"id": str(conversation.id), "conversation_type": conversation.conversation_type, "status": conversation.status, "peer": compact_user(peer, viewer) if peer else None, "last_message": message_payload(conversation.last_message, viewer) if conversation.last_message else None, "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None, "unread_count": unread_count, "archived": bool(participant.archived_at), "muted_until": participant.muted_until.isoformat() if participant.muted_until else None, "marked_unread": participant.marked_unread, "request_state": participant.request_state, "created_at": conversation.created_at.isoformat(), "updated_at": conversation.updated_at.isoformat()}


def mark_read(conversation, user, message=None):
    participant = ensure_membership(conversation, user)
    message = message or message_queryset_for(user, conversation).order_by("-created_at").first()
    now = timezone.now()
    participant.last_read_message = message
    participant.last_read_at = now
    participant.marked_unread = False
    participant.save(update_fields=["last_read_message", "last_read_at", "marked_unread", "updated_at"])
    if message and user.privacy_settings.send_read_receipts:
        ids = message_queryset_for(user, conversation).exclude(sender=user).filter(created_at__lte=message.created_at).values_list("id", flat=True)
        for item_id in ids:
            MessageReadReceipt.objects.get_or_create(message_id=item_id, user=user)
    return participant


def delivery_ack(message, user, device_id=""):
    ensure_membership(message.conversation, user)
    if message.sender_id != user.phone_number:
        MessageDeliveryReceipt.objects.get_or_create(message=message, user=user, device_id=device_id[:120])
        if message.status == Message.STATUS_SENT:
            message.status = Message.STATUS_DELIVERED
            message.save(update_fields=["status", "updated_at"])


def update_presence(user, state=UserPresence.STATE_ONLINE):
    now = timezone.now()
    presence, _ = UserPresence.objects.get_or_create(user=user)
    presence.state = state
    presence.last_heartbeat_at = now
    if state in {UserPresence.STATE_OFFLINE, UserPresence.STATE_RECENTLY_ACTIVE}:
        presence.last_seen_at = now
    presence.save()
    return presence


def presence_payload(target, viewer):
    ensure_profile_records(target)
    if users_blocked_between(viewer, target):
        return {"state": "hidden", "last_seen_at": None}
    setting = target.privacy_settings.show_online_status
    if setting == "no_one" or (setting == "people_i_follow" and not follows(target, viewer)):
        return {"state": "hidden", "last_seen_at": None}
    presence = getattr(target, "presence", None)
    last_seen_setting = target.privacy_settings.show_last_seen
    show_last_seen = last_seen_setting == "everyone" or (last_seen_setting == "people_i_follow" and follows(target, viewer))
    return {"state": presence.state if presence else UserPresence.STATE_OFFLINE, "last_seen_at": presence.last_seen_at.isoformat() if presence and presence.last_seen_at and show_last_seen else None}


def edit_message(message, user, text):
    if message.sender != user:
        raise PermissionError("Only the sender can edit this message.")
    if message.message_type != Message.TYPE_TEXT:
        raise ValueError("Only text messages can be edited.")
    if message.deleted_for_everyone_at:
        raise ValueError("Deleted messages cannot be edited.")
    if timezone.now() > message.created_at + EDIT_WINDOW:
        raise PermissionError("The message edit window has expired.")
    message.text = clean_message_text(text)
    message.is_edited = True
    message.edited_at = timezone.now()
    message.save(update_fields=["text", "is_edited", "edited_at", "updated_at"])
    return message


def delete_for_everyone(message, user):
    if message.sender != user:
        raise PermissionError("Only the sender can delete this message for everyone.")
    if timezone.now() > message.created_at + DELETE_FOR_EVERYONE_WINDOW:
        raise PermissionError("The delete-for-everyone window has expired.")
    message.deleted_for_everyone_at = timezone.now()
    message.status = Message.STATUS_DELETED
    message.save(update_fields=["deleted_for_everyone_at", "status", "updated_at"])
    return message


def report_context(message=None, conversation=None):
    def item(row):
        return {"id": str(row.id), "sender": row.sender.username, "message_type": row.message_type, "text": row.text[:200], "created_at": row.created_at.isoformat()}
    if message:
        before = [item(row) for row in Message.objects.filter(conversation=message.conversation, created_at__lt=message.created_at).select_related("sender").order_by("-created_at")[:2]]
        after = [item(row) for row in Message.objects.filter(conversation=message.conversation, created_at__gt=message.created_at).select_related("sender").order_by("created_at")[:2]]
        return {"reported_message": str(message.id), "before": before, "after": after}
    if conversation:
        return {"conversation": str(conversation.id), "recent": [item(row) for row in conversation.messages.select_related("sender").order_by("-created_at")[:5]]}
    return {}
