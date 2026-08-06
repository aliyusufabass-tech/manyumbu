import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .messaging_services import clean_message_text, validate_attachment, attachment_payload, MAX_PINS_PER_CONVERSATION, EDIT_WINDOW, DELETE_FOR_EVERYONE_WINDOW
from .models import (
    AdminAnnouncement, Group, GroupArchive, GroupAuditLog, GroupBan, GroupClearState, GroupInvitation, GroupJoinRequest, GroupMember, GroupMessage, GroupSettings, GroupMessageAttachment, GroupMessageDeletion, GroupMessageDeliveryReceipt, GroupMessagePin, GroupMessageReaction, GroupMessageReadReceipt, GroupMessageReport, GroupMessageStar, GroupMute, GroupReport, GroupRestriction, Message, MessageAttachment, Notification, NotificationBatch, NotificationDelivery, NotificationPreference, PushNotificationDelivery, UserDevice,
)
from .profile_views import compact_user
from .storage import absolute_media_url
from .services import hash_token, users_blocked_between

ROLE_RANK = {Group.ROLE_MEMBER: 1, Group.ROLE_MODERATOR: 2, Group.ROLE_ADMIN: 3, Group.ROLE_OWNER: 4}


def active_member(group, user):
    return GroupMember.objects.filter(group=group, user=user, status=GroupMember.STATUS_ACTIVE).first()


def require_member(group, user):
    member = active_member(group, user)
    if not member or is_banned(group, user):
        raise PermissionError("Active group membership is required.")
    if group.status != Group.STATUS_ACTIVE:
        raise PermissionError("This group is not active.")
    return member


def has_role(member, required):
    return ROLE_RANK.get(member.role, 0) >= ROLE_RANK.get(required, 0)


def permission_required(permission_value):
    return {Group.PERM_EVERYONE: Group.ROLE_MEMBER, Group.PERM_MODERATORS: Group.ROLE_MODERATOR, Group.PERM_ADMINS: Group.ROLE_ADMIN, Group.PERM_OWNER: Group.ROLE_OWNER}.get(permission_value, Group.ROLE_OWNER)


def require_permission(group, user, field):
    member = require_member(group, user)
    if not has_role(member, permission_required(getattr(group, field))):
        raise PermissionError("Your group role does not allow this action.")
    return member


def is_banned(group, user):
    now = timezone.now()
    return GroupBan.objects.filter(group=group, user=user, revoked_at__isnull=True).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)).exists()


def is_restricted(group, user, kind="messages"):
    now = timezone.now()
    restriction = GroupRestriction.objects.filter(group=group, user=user, revoked_at__isnull=True).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)).first()
    if not restriction:
        return False
    if kind == "media":
        return restriction.restrict_media
    if kind == "links":
        return restriction.restrict_links
    return restriction.restrict_messages


def audit(group, actor, action, target="", metadata=None):
    return GroupAuditLog.objects.create(group=group, actor=actor, action=action, target=str(target or ""), metadata=metadata or {})


def ensure_notification_preferences(user):
    return NotificationPreference.objects.get_or_create(user=user)[0]


def notification_payload(notification):
    return {"id": str(notification.uuid), "type": notification.notification_type, "object_type": notification.object_type, "object_uuid": notification.object_uuid, "message": notification.message, "payload": notification.safe_payload, "is_read": notification.is_read, "read_at": notification.read_at.isoformat() if notification.read_at else None, "seen_at": notification.seen_at.isoformat() if notification.seen_at else None, "priority": notification.priority, "grouping_key": notification.grouping_key, "created_at": notification.created_at.isoformat()}


def create_in_app_notification(recipient, actor, notification_type, message, object_type="", object_uuid="", payload=None, grouping_key="", priority="normal"):
    prefs = ensure_notification_preferences(recipient)
    if not prefs.in_app_enabled and priority != "security":
        return None
    notification = Notification.objects.create(recipient=recipient, actor=actor, notification_type=notification_type, object_type=object_type, object_uuid=str(object_uuid or ""), safe_payload=payload or {}, message=message[:180], grouping_key=grouping_key, priority=priority)
    NotificationDelivery.objects.create(notification=notification, channel="in_app", status="delivered", attempted_at=timezone.now())
    if grouping_key:
        batch, created = NotificationBatch.objects.get_or_create(recipient=recipient, grouping_key=grouping_key, defaults={"notification_type": notification_type, "latest_notification": notification})
        if not created:
            batch.count += 1
            batch.latest_notification = notification
            batch.save(update_fields=["count", "latest_notification", "updated_at"])
    queue_push_notification(notification)
    return notification


def queue_push_notification(notification):
    prefs = ensure_notification_preferences(notification.recipient)
    if not prefs.push_enabled:
        return []
    deliveries = []
    for device in UserDevice.objects.filter(user=notification.recipient, revoked_at__isnull=True).exclude(push_token=""):
        deliveries.append(PushNotificationDelivery.objects.create(notification=notification, device=device, status="not_configured", deep_link=notification.safe_payload.get("deep_link", "")))
    notification.push_status = "not_configured" if deliveries else "not_sent"
    notification.save(update_fields=["push_status"])
    return deliveries


@transaction.atomic
def create_group(owner, payload, image=None):
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("Group name is required.")
    if len(name) > 120:
        raise ValueError("Group name must be 120 characters or fewer.")
    description = str(payload.get("description", ""))[:1000]
    group = Group.objects.create(owner=owner, name=name, description=description, privacy=payload.get("privacy", Group.PRIVACY_PRIVATE), image=image, who_can_join=payload.get("who_can_join", Group.JOIN_INVITE), who_can_send_messages=payload.get("who_can_send_messages", Group.PERM_EVERYONE), who_can_add_members=payload.get("who_can_add_members", Group.PERM_ADMINS), who_can_pin_messages=payload.get("who_can_pin_messages", Group.PERM_MODERATORS), who_can_mention_everyone=payload.get("who_can_mention_everyone", Group.PERM_ADMINS))
    GroupSettings.objects.create(group=group, require_join_approval=group.who_can_join == Group.JOIN_APPROVAL)
    GroupMember.objects.create(group=group, user=owner, role=Group.ROLE_OWNER)
    identifiers = list(dict.fromkeys(payload.get("members", []) or payload.get("initial_members", []) or []))
    for ident in identifiers[: group.maximum_members - 1]:
        target = get_user_by_identifier(ident)
        add_group_member(group, owner, target, role=Group.ROLE_MEMBER, notify=True)
    refresh_member_count(group)
    audit(group, owner, "group_created", group.id)
    return group


def get_user_by_identifier(identifier):
    User = get_user_model()
    return User.objects.get(Q(username__iexact=str(identifier)) | Q(phone_number=str(identifier)) | Q(email__iexact=str(identifier)))


@transaction.atomic
def add_group_member(group, actor, user, role=Group.ROLE_MEMBER, notify=True):
    require_permission(group, actor, "who_can_add_members")
    if user == group.owner and role != Group.ROLE_OWNER:
        role = Group.ROLE_OWNER
    if not user.is_active or not user.is_email_verified:
        raise PermissionError("Inactive users cannot be added.")
    if users_blocked_between(actor, user):
        raise PermissionError("Blocked users cannot be added.")
    if is_banned(group, user):
        raise PermissionError("Banned users cannot join this group.")
    existing = active_member(group, user)
    if existing:
        raise ValueError("User is already a group member.")
    if group.member_count >= group.maximum_members:
        raise ValueError("Group member limit has been reached.")
    member, created = GroupMember.objects.update_or_create(group=group, user=user, defaults={"role": role, "status": GroupMember.STATUS_ACTIVE})
    refresh_member_count(group)
    if notify and user != actor:
        create_in_app_notification(user, actor, "group_added", f"You were added to {group.name}.", "group", group.id, {"group_id": str(group.id), "deep_link": f"manyumbu://groups/{group.id}"}, f"group:{group.id}:added")
    audit(group, actor, "member_added", user.username, {"role": role})
    return member



@transaction.atomic
def update_group_member_role(group, actor, user, new_role):
    actor_member = require_member(group, actor)
    target_member = require_member(group, user)
    if new_role not in {Group.ROLE_MEMBER, Group.ROLE_MODERATOR, Group.ROLE_ADMIN}:
        raise ValueError("Unsupported group role.")
    if target_member.role == Group.ROLE_OWNER:
        raise PermissionError("Owner role cannot be changed here.")
    if actor_member.role != Group.ROLE_OWNER:
        if not has_role(actor_member, Group.ROLE_ADMIN):
            raise PermissionError("Only owners and admins can manage roles.")
        if ROLE_RANK[actor_member.role] <= ROLE_RANK[target_member.role] or ROLE_RANK[actor_member.role] <= ROLE_RANK[new_role]:
            raise PermissionError("Your role cannot change this member role.")
    target_member.role = new_role
    target_member.save(update_fields=["role", "updated_at"])
    audit(group, actor, "member_role_updated", user.username, {"role": new_role})
    if user != actor:
        create_in_app_notification(user, actor, "group_role_changed", f"Your role in {group.name} is now {new_role}.", "group", group.id, {"group_id": str(group.id), "role": new_role})
    return target_member

@transaction.atomic
def remove_group_member(group, actor, user):
    actor_member = require_member(group, actor)
    target_member = require_member(group, user)
    if target_member.role == Group.ROLE_OWNER:
        raise PermissionError("The group owner cannot be removed.")
    if not has_role(actor_member, Group.ROLE_ADMIN) or ROLE_RANK[actor_member.role] <= ROLE_RANK[target_member.role]:
        raise PermissionError("Your role cannot remove this member.")
    target_member.status = GroupMember.STATUS_REMOVED
    target_member.save(update_fields=["status", "updated_at"])
    refresh_member_count(group)
    create_system_message(group, actor, f"{user.username} was removed from the group.")
    audit(group, actor, "member_removed", user.username)
    return target_member


@transaction.atomic
def leave_group(group, user):
    member = require_member(group, user)
    if member.role == Group.ROLE_OWNER:
        others = GroupMember.objects.filter(group=group, status=GroupMember.STATUS_ACTIVE).exclude(user=user)
        if others.exists():
            raise PermissionError("Transfer ownership before leaving this group.")
        group.status = Group.STATUS_DELETED
        group.deleted_at = timezone.now()
        group.save(update_fields=["status", "deleted_at", "updated_at"])
    member.status = GroupMember.STATUS_LEFT
    member.save(update_fields=["status", "updated_at"])
    refresh_member_count(group)
    create_system_message(group, user, f"{user.username} left the group.")
    audit(group, user, "member_left", user.username)
    return member


@transaction.atomic
def transfer_ownership(group, owner, target, password_confirmed=False):
    owner_member = require_member(group, owner)
    if owner_member.role != Group.ROLE_OWNER:
        raise PermissionError("Only the owner can transfer ownership.")
    if not password_confirmed:
        raise PermissionError("Recent authentication is required to transfer ownership.")
    target_member = require_member(group, target)
    if is_banned(group, target) or users_blocked_between(owner, target):
        raise PermissionError("This member is not eligible for ownership.")
    owner_member.role = Group.ROLE_ADMIN
    owner_member.save(update_fields=["role", "updated_at"])
    target_member.role = Group.ROLE_OWNER
    target_member.save(update_fields=["role", "updated_at"])
    group.owner = target
    group.save(update_fields=["owner", "updated_at"])
    audit(group, owner, "ownership_transferred", target.username)
    create_in_app_notification(target, owner, "group_ownership_transferred", f"You now own {group.name}.", "group", group.id, {"group_id": str(group.id)})
    return target_member


def refresh_member_count(group):
    group.member_count = GroupMember.objects.filter(group=group, status=GroupMember.STATUS_ACTIVE).count()
    group.save(update_fields=["member_count", "updated_at"])


def create_system_message(group, actor, text):
    msg = GroupMessage.objects.create(group=group, sender=actor, message_type=Message.TYPE_SYSTEM, text=text, is_system=True)
    group.last_message_at = msg.created_at
    group.save(update_fields=["last_message_at", "updated_at"])
    return msg


def group_payload(group, viewer):
    member = active_member(group, viewer)
    return {"id": str(group.id), "name": group.name, "description": group.description, "image": absolute_media_url(group.image), "owner": compact_user(group.owner, viewer), "privacy": group.privacy, "member_count": group.member_count, "maximum_members": group.maximum_members, "status": group.status, "viewer_role": member.role if member else None, "viewer_can_send": bool(member and can_send(group, viewer, raise_error=False)), "muted_until": member.muted_until.isoformat() if member and member.muted_until else None, "archived": bool(member and member.archived_at), "last_message_at": group.last_message_at.isoformat() if group.last_message_at else None, "settings": {"who_can_join": group.who_can_join, "who_can_send_messages": group.who_can_send_messages, "who_can_add_members": group.who_can_add_members, "who_can_pin_messages": group.who_can_pin_messages, "who_can_mention_everyone": group.who_can_mention_everyone}, "created_at": group.created_at.isoformat(), "updated_at": group.updated_at.isoformat()}


def can_send(group, user, raise_error=True):
    try:
        member = require_permission(group, user, "who_can_send_messages")
        if is_restricted(group, user, "messages"):
            raise PermissionError("You are restricted from sending messages in this group.")
        return member
    except PermissionError:
        if raise_error:
            raise
        return None


def group_message_queryset(user, group):
    member = require_member(group, user)
    qs = GroupMessage.objects.filter(group=group).exclude(deleted_for__user=user).select_related("sender", "reply_to", "reply_to__sender").prefetch_related("attachments", "reactions__user")
    if member.cleared_before:
        qs = qs.filter(created_at__gt=member.cleared_before)
    return qs


@transaction.atomic
def create_group_message(group, sender, payload, files=None):
    can_send(group, sender)
    message_type = payload.get("message_type", Message.TYPE_TEXT)
    files = files or []
    if files and is_restricted(group, sender, "media"):
        raise PermissionError("You are restricted from sending media in this group.")
    text = clean_message_text(payload.get("text", ""), required_for_text=message_type == Message.TYPE_TEXT and not files and not payload.get("shared_content") and not payload.get("location") and not payload.get("contact"))
    if "@everyone" in text and not has_role(active_member(group, sender), permission_required(group.who_can_mention_everyone)):
        raise PermissionError("Your role cannot mention everyone.")
    client_id = str(payload.get("client_message_id", ""))[:80]
    if client_id:
        existing = GroupMessage.objects.filter(sender=sender, client_message_id=client_id).first()
        if existing:
            return existing, False
    reply_to = GroupMessage.objects.get(id=payload["reply_to_id"], group=group) if payload.get("reply_to_id") else None
    mentioned = [word[1:].lower() for word in text.split() if word.startswith("@")]
    msg = GroupMessage.objects.create(group=group, sender=sender, message_type=message_type, text=text, reply_to=reply_to, client_message_id=client_id, shared_content=payload.get("shared_content", {}), location_payload=payload.get("location", {}), contact_payload=payload.get("contact", {}), is_forwarded=bool(payload.get("is_forwarded")), forwarded_from=payload.get("forwarded_from", {}), mentioned_usernames=mentioned)
    for upload in files:
        kind = payload.get("attachment_kind") or message_type
        filename, mime = validate_attachment(upload, kind, payload.get("duration"), payload.get("width"), payload.get("height"))
        GroupMessageAttachment.objects.create(message=msg, owner=sender, file=upload, kind=kind, file_name=filename, mime_type=mime, file_size=getattr(upload, "size", 0) or 0, width=payload.get("width") or None, height=payload.get("height") or None, duration=payload.get("duration") or None, waveform=payload.get("waveform", []), processing_status=MessageAttachment.PROCESSING_PENDING if kind == MessageAttachment.KIND_VIDEO else MessageAttachment.PROCESSING_READY)
    group.last_message_at = msg.created_at
    group.save(update_fields=["last_message_at", "updated_at"])
    GroupMember.objects.filter(group=group, status=GroupMember.STATUS_ACTIVE).exclude(user=sender).update(marked_unread=True, archived_at=None)
    notify_group_message(group, sender, msg)
    return msg, True


def notify_group_message(group, sender, msg):
    members = GroupMember.objects.filter(group=group, status=GroupMember.STATUS_ACTIVE).exclude(user=sender).select_related("user")
    for member in members:
        prefs = ensure_notification_preferences(member.user)
        if not prefs.group_messages or member.muted_until and member.muted_until > timezone.now():
            continue
        preview = f"New message in {group.name}" if not prefs.notification_previews else f"{sender.username}: {msg.text[:80] or msg.message_type}"
        create_in_app_notification(member.user, sender, "group_message", preview, "group", group.id, {"group_id": str(group.id), "message_id": str(msg.id), "deep_link": f"manyumbu://groups/{group.id}"}, f"group:{group.id}:messages")
    mentioned_members = GroupMember.objects.filter(group=group, status=GroupMember.STATUS_ACTIVE, user__username__in=msg.mentioned_usernames).exclude(user=sender).select_related("user")
    for member in mentioned_members:
        create_in_app_notification(member.user, sender, "group_mention", f"You were mentioned in {group.name}.", "group_message", msg.id, {"group_id": str(group.id), "message_id": str(msg.id)})


def group_attachment_payload(a):
    return attachment_payload(a)


def group_message_payload(msg, viewer):
    deleted = bool(msg.deleted_for_everyone_at or msg.removed_by_moderator_id)
    return {"id": str(msg.id), "group_id": str(msg.group_id), "sender": compact_user(msg.sender, viewer), "message_type": msg.message_type, "text": "" if deleted else msg.text, "reply_to": {"id": str(msg.reply_to_id), "text": msg.reply_to.text[:120], "sender": compact_user(msg.reply_to.sender, viewer)} if msg.reply_to_id else None, "is_forwarded": msg.is_forwarded, "shared_content": {} if deleted else msg.shared_content, "location": {} if deleted else msg.location_payload, "contact": {} if deleted else msg.contact_payload, "mentioned_usernames": msg.mentioned_usernames, "status": Message.STATUS_DELETED if deleted else msg.status, "is_system": msg.is_system, "is_edited": msg.is_edited, "edited_at": msg.edited_at.isoformat() if msg.edited_at else None, "deleted_for_everyone_at": msg.deleted_for_everyone_at.isoformat() if msg.deleted_for_everyone_at else None, "removed_by_moderator": bool(msg.removed_by_moderator_id), "attachments": [] if deleted else [group_attachment_payload(a) for a in msg.attachments.all()], "reactions": [{"username": r.user.username, "reaction": r.reaction} for r in msg.reactions.select_related("user")], "viewer_has_starred": GroupMessageStar.objects.filter(message=msg, user=viewer).exists(), "viewer_has_pinned": GroupMessagePin.objects.filter(message=msg, group=msg.group).exists(), "read_count": msg.read_receipts.exclude(user=msg.sender).count(), "delivered_count": msg.delivery_receipts.exclude(user=msg.sender).count(), "created_at": msg.created_at.isoformat(), "updated_at": msg.updated_at.isoformat()}


def create_invitation(group, actor, expires_hours=24, max_uses=None):
    require_permission(group, actor, "who_can_create_invites")
    token = secrets.token_urlsafe(32)
    invite = GroupInvitation.objects.create(group=group, creator=actor, token_hash=hash_token(token), token_preview=token[:10], expires_at=timezone.now() + timedelta(hours=int(expires_hours)) if expires_hours else None, max_uses=max_uses)
    audit(group, actor, "invitation_created", invite.id)
    return token, invite


@transaction.atomic
def join_by_invitation(user, token):
    invite = GroupInvitation.objects.select_for_update().select_related("group").get(token_hash=hash_token(token), revoked_at__isnull=True)
    if invite.expires_at and invite.expires_at <= timezone.now():
        raise PermissionError("Invitation link has expired.")
    if invite.max_uses is not None and invite.use_count >= invite.max_uses:
        raise PermissionError("Invitation link has reached its use limit.")
    group = invite.group
    if is_banned(group, user):
        raise PermissionError("Banned users cannot join this group.")
    if group.who_can_join == Group.JOIN_APPROVAL or group.settings.require_join_approval:
        req, _ = GroupJoinRequest.objects.get_or_create(group=group, requester=user, status=GroupJoinRequest.STATUS_PENDING)
        return group, req, False
    member = GroupMember.objects.update_or_create(group=group, user=user, defaults={"role": Group.ROLE_MEMBER, "status": GroupMember.STATUS_ACTIVE})[0]
    invite.use_count += 1
    invite.save(update_fields=["use_count"])
    refresh_member_count(group)
    audit(group, user, "member_joined_by_invite", user.username)
    return group, member, True


def mark_group_read(group, user, message=None):
    member = require_member(group, user)
    message = message or group_message_queryset(user, group).order_by("-created_at").first()
    now = timezone.now()
    member.last_read_message = message
    member.last_read_at = now
    member.marked_unread = False
    member.save(update_fields=["last_read_message", "last_read_at", "marked_unread", "updated_at"])
    if message:
        GroupMessageReadReceipt.objects.get_or_create(message=message, user=user)
    return member
