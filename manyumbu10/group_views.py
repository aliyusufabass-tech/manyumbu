import json
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .group_services import active_member, add_group_member, audit, create_group, create_group_message, create_in_app_notification, create_invitation, group_message_payload, group_message_queryset, group_payload, join_by_invitation, leave_group, mark_group_read, refresh_member_count, remove_group_member, require_member, require_permission, transfer_ownership
from .models import AdminAnnouncement, AdminAuditLog, Group, GroupArchive, GroupBan, GroupClearState, GroupInvitation, GroupJoinRequest, GroupMember, GroupMessage, GroupMessageAttachment, GroupMessageDeletion, GroupMessageDeliveryReceipt, GroupMessagePin, GroupMessageReaction, GroupMessageReport, GroupMessageStar, GroupMute, GroupReport, GroupRestriction, Notification, NotificationPreference
from .profile_views import AuthenticatedView, compact_user, get_target, page
from .views import body, response


def parse_payload(request):
    if request.content_type and request.content_type.startswith("multipart/"):
        payload = request.POST.dict()
        for key in ["members", "initial_members", "shared_content", "location", "contact", "forwarded_from", "waveform"]:
            if key in payload:
                try: payload[key] = json.loads(payload[key])
                except Exception: payload[key] = [] if key in {"members", "initial_members", "waveform"} else {}
        return payload
    return body(request)


@method_decorator(csrf_exempt, name="dispatch")
class GroupListView(AuthenticatedView):
    def get(self, request):
        qs = Group.objects.filter(members__user=request.user_obj, members__status=GroupMember.STATUS_ACTIVE).distinct()
        if request.GET.get("type") == "public": qs = Group.objects.filter(privacy=Group.PRIVACY_PUBLIC, status=Group.STATUS_ACTIVE)
        if request.GET.get("archived") != "1": qs = qs.exclude(members__user=request.user_obj, members__archived_at__isnull=False)
        q = request.GET.get("q", "").strip()
        if q: qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        return response(True, "Groups loaded.", page(request, qs.order_by("-last_message_at", "-updated_at"), lambda g: group_payload(g, request.user_obj)))
    def post(self, request):
        try:
            group = create_group(request.user_obj, parse_payload(request), request.FILES.get("image"))
            return response(True, "Group created.", {"group": group_payload(group, request.user_obj)}, status=201)
        except Exception as exc: return response(False, str(exc), status=403 if isinstance(exc, PermissionError) else 400)


@method_decorator(csrf_exempt, name="dispatch")
class GroupDetailView(AuthenticatedView):
    def get(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id)
            if group.privacy != Group.PRIVACY_PUBLIC: require_member(group, request.user_obj)
            return response(True, "Group loaded.", {"group": group_payload(group, request.user_obj)})
        except Group.DoesNotExist: return response(False, "Group was not found.", status=404)
        except PermissionError as exc: return response(False, str(exc), status=403)
    def patch(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id); require_permission(group, request.user_obj, "who_can_edit_info"); payload = parse_payload(request)
            for field in ["name", "description", "privacy", "who_can_join", "who_can_send_messages", "who_can_add_members", "who_can_approve_members", "who_can_create_invites", "who_can_pin_messages", "who_can_mention_everyone"]:
                if field in payload: setattr(group, field, payload[field])
            if request.FILES.get("image"): group.image = request.FILES["image"]
            group.full_clean(); group.save(); audit(group, request.user_obj, "group_updated", group.id)
            return response(True, "Group updated.", {"group": group_payload(group, request.user_obj)})
        except Group.DoesNotExist: return response(False, "Group was not found.", status=404)
        except Exception as exc: return response(False, str(exc), status=403 if isinstance(exc, PermissionError) else 400)
    def delete(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id); member = require_member(group, request.user_obj)
            if member.role != Group.ROLE_OWNER: return response(False, "Only the owner can delete this group.", status=403)
            group.status = Group.STATUS_DELETED; group.deleted_at = timezone.now(); group.save(update_fields=["status", "deleted_at", "updated_at"]); audit(group, request.user_obj, "group_deleted", group.id)
            return response(True, "Group deleted.")
        except Group.DoesNotExist: return response(False, "Group was not found.", status=404)
        except PermissionError as exc: return response(False, str(exc), status=403)


@method_decorator(csrf_exempt, name="dispatch")
class GroupMembersView(AuthenticatedView):
    def get(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id); require_member(group, request.user_obj)
            qs = GroupMember.objects.filter(group=group, status=GroupMember.STATUS_ACTIVE).select_related("user").order_by("-role", "user__username")
            return response(True, "Group members loaded.", page(request, qs, lambda m: {"user": compact_user(m.user, request.user_obj), "role": m.role, "joined_at": m.joined_at.isoformat()}))
        except Exception as exc: return response(False, str(exc), status=403)
    def post(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id); payload = body(request); added = []
            for ident in payload.get("members", [payload.get("username")]):
                if ident: added.append(add_group_member(group, request.user_obj, get_target(ident)))
            return response(True, "Members added.", {"members": [compact_user(m.user, request.user_obj) for m in added]})
        except Exception as exc: return response(False, str(exc), status=403)
    def delete(self, request, group_id, user_identifier):
        try: remove_group_member(Group.objects.get(id=group_id), request.user_obj, get_target(user_identifier)); return response(True, "Member removed.")
        except Exception as exc: return response(False, str(exc), status=403)

@method_decorator(csrf_exempt, name="dispatch")
class GroupMembershipActionView(AuthenticatedView):
    def post(self, request, group_id, action):
        try:
            group = Group.objects.get(id=group_id); payload = body(request)
            if action == "leave": leave_group(group, request.user_obj)
            elif action == "transfer-ownership": transfer_ownership(group, request.user_obj, get_target(payload.get("username", "")), password_confirmed=bool(payload.get("password_confirmed")))
            elif action == "roles":
                require_permission(group, request.user_obj, "who_can_add_members"); member = require_member(group, get_target(payload.get("username", ""))); new_role = payload.get("role", Group.ROLE_MEMBER)
                if new_role == Group.ROLE_OWNER: return response(False, "Use ownership transfer for owners.", status=400)
                if member.role == Group.ROLE_OWNER: return response(False, "Owner role cannot be changed here.", status=403)
                member.role = new_role; member.save(update_fields=["role", "updated_at"]); audit(group, request.user_obj, "member_role_updated", member.user.username, {"role": new_role})
            elif action == "ban":
                require_permission(group, request.user_obj, "who_can_add_members"); target = get_target(payload.get("username", ""))
                if target == group.owner: return response(False, "Owner cannot be banned.", status=403)
                GroupBan.objects.update_or_create(group=group, user=target, defaults={"banned_by": request.user_obj, "reason": payload.get("reason", "")[:280], "revoked_at": None}); GroupMember.objects.filter(group=group, user=target).update(status=GroupMember.STATUS_BANNED); refresh_member_count(group); audit(group, request.user_obj, "member_banned", target.username)
            elif action == "restrict":
                require_permission(group, request.user_obj, "who_can_add_members"); target = get_target(payload.get("username", "")); GroupRestriction.objects.update_or_create(group=group, user=target, defaults={"restricted_by": request.user_obj, "restrict_messages": bool(payload.get("restrict_messages", True)), "restrict_media": bool(payload.get("restrict_media", False)), "restrict_links": bool(payload.get("restrict_links", False)), "reason": payload.get("reason", "")[:280], "expires_at": timezone.now() + timedelta(hours=int(payload.get("hours", 24))), "revoked_at": None}); audit(group, request.user_obj, "member_restricted", target.username)
            elif action == "report":
                report, _ = GroupReport.objects.get_or_create(group=group, reporter=request.user_obj, reason=payload.get("reason", "other"), defaults={"details": payload.get("details", "")[:1000], "context_snapshot": {"group": str(group.id), "name": group.name}}); return response(True, "Group report submitted.", {"report_id": report.id})
            elif action == "mute":
                member = require_member(group, request.user_obj); until = timezone.now() + timedelta(hours=int(payload.get("hours", 8))); member.muted_until = until; member.save(update_fields=["muted_until", "updated_at"]); GroupMute.objects.update_or_create(group=group, user=request.user_obj, defaults={"muted_until": until})
            elif action == "archive": member = require_member(group, request.user_obj); member.archived_at = timezone.now(); member.save(update_fields=["archived_at", "updated_at"]); GroupArchive.objects.get_or_create(group=group, user=request.user_obj)
            elif action == "unarchive": member = require_member(group, request.user_obj); member.archived_at = None; member.save(update_fields=["archived_at", "updated_at"]); GroupArchive.objects.filter(group=group, user=request.user_obj).delete()
            elif action == "clear": member = require_member(group, request.user_obj); member.cleared_before = timezone.now(); member.save(update_fields=["cleared_before", "updated_at"]); GroupClearState.objects.update_or_create(group=group, user=request.user_obj, defaults={"cleared_before": member.cleared_before})
            else: return response(False, "Unknown group action.", status=400)
            return response(True, "Group action completed.", {"group": group_payload(group, request.user_obj)})
        except Exception as exc: return response(False, str(exc), status=403)
    def delete(self, request, group_id, action):
        if action != "mute": return response(False, "Unknown group action.", status=400)
        group = Group.objects.get(id=group_id); member = require_member(group, request.user_obj); member.muted_until = None; member.save(update_fields=["muted_until", "updated_at"]); GroupMute.objects.filter(group=group, user=request.user_obj).delete(); return response(True, "Group unmuted.", {"group": group_payload(group, request.user_obj)})


@method_decorator(csrf_exempt, name="dispatch")
class GroupMessagesView(AuthenticatedView):
    def get(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id); qs = group_message_queryset(request.user_obj, group).order_by("-created_at"); before = request.GET.get("before"); after = request.GET.get("after")
            if before:
                parsed = parse_datetime(before.replace(" ", "+")) or parse_datetime(before)
                if parsed: qs = qs.filter(created_at__lt=parsed)
            if after:
                parsed = parse_datetime(after.replace(" ", "+")) or parse_datetime(after)
                if parsed: qs = qs.filter(created_at__gt=parsed).order_by("created_at")
            return response(True, "Group messages loaded.", page(request, qs, lambda m: group_message_payload(m, request.user_obj), default_size=30))
        except Exception as exc: return response(False, str(exc), status=403)
    def post(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id); msg, created = create_group_message(group, request.user_obj, parse_payload(request), request.FILES.getlist("attachments") or request.FILES.getlist("attachment"))
            return response(True, "Group message sent.", {"message": group_message_payload(msg, request.user_obj), "deduplicated": not created}, status=201 if created else 200)
        except Exception as exc: return response(False, str(exc), status=403 if isinstance(exc, PermissionError) else 400)


@method_decorator(csrf_exempt, name="dispatch")
class GroupMessageActionView(AuthenticatedView):
    def patch(self, request, message_id):
        try:
            msg = GroupMessage.objects.get(id=message_id); require_member(msg.group, request.user_obj)
            if msg.sender != request.user_obj or msg.is_system or timezone.now() > msg.created_at + timedelta(minutes=15): return response(False, "Message cannot be edited.", status=403)
            msg.text = body(request).get("text", "")[:5000]; msg.is_edited = True; msg.edited_at = timezone.now(); msg.save(update_fields=["text", "is_edited", "edited_at", "updated_at"]); return response(True, "Group message updated.", {"message": group_message_payload(msg, request.user_obj)})
        except GroupMessage.DoesNotExist: return response(False, "Group message was not found.", status=404)
    def post(self, request, message_id, action):
        try:
            msg = GroupMessage.objects.get(id=message_id); require_member(msg.group, request.user_obj); payload = body(request)
            if action == "react": GroupMessageReaction.objects.update_or_create(message=msg, user=request.user_obj, defaults={"reaction": payload.get("reaction", "like")})
            elif action == "pin": require_permission(msg.group, request.user_obj, "who_can_pin_messages"); GroupMessagePin.objects.get_or_create(message=msg, group=msg.group, defaults={"pinned_by": request.user_obj})
            elif action == "star": GroupMessageStar.objects.get_or_create(message=msg, user=request.user_obj)
            elif action == "read": mark_group_read(msg.group, request.user_obj, msg)
            elif action == "delivered":
                if msg.sender != request.user_obj: GroupMessageDeliveryReceipt.objects.get_or_create(message=msg, user=request.user_obj, device_id=payload.get("device_id", "")[:120])
            elif action == "report": report, _ = GroupMessageReport.objects.get_or_create(message=msg, reporter=request.user_obj, reason=payload.get("reason", "other"), defaults={"details": payload.get("details", "")[:1000], "context_snapshot": {"message": str(msg.id), "group": str(msg.group_id), "text": msg.text[:200]}}); return response(True, "Group message report submitted.", {"report_id": report.id})
            elif action == "forward": target_group = Group.objects.get(id=payload.get("group_id")); forwarded, _ = create_group_message(target_group, request.user_obj, {"message_type": msg.message_type, "text": payload.get("note", msg.text), "is_forwarded": True, "forwarded_from": {"group_message_id": str(msg.id)}, "shared_content": msg.shared_content}, []); return response(True, "Group message forwarded.", {"message": group_message_payload(forwarded, request.user_obj)}, status=201)
            else: return response(False, "Unknown group message action.", status=400)
            return response(True, "Group message action completed.", {"message": group_message_payload(msg, request.user_obj)})
        except Exception as exc: return response(False, str(exc), status=403)
    def delete(self, request, message_id, action):
        try:
            msg = GroupMessage.objects.get(id=message_id); member = require_member(msg.group, request.user_obj)
            if action == "for-me": GroupMessageDeletion.objects.get_or_create(message=msg, user=request.user_obj)
            elif action == "for-everyone":
                if msg.sender == request.user_obj and timezone.now() <= msg.created_at + timedelta(hours=24): msg.deleted_for_everyone_at = timezone.now(); msg.save(update_fields=["deleted_for_everyone_at", "updated_at"])
                elif member.role in [Group.ROLE_OWNER, Group.ROLE_ADMIN, Group.ROLE_MODERATOR]: msg.removed_by_moderator = request.user_obj; msg.moderation_reason = body(request).get("reason", "")[:280]; msg.save(update_fields=["removed_by_moderator", "moderation_reason", "updated_at"]); audit(msg.group, request.user_obj, "group_message_removed", msg.id)
                else: return response(False, "You cannot delete this message for everyone.", status=403)
            elif action == "react": GroupMessageReaction.objects.filter(message=msg, user=request.user_obj).delete()
            elif action == "pin": GroupMessagePin.objects.filter(message=msg, group=msg.group).delete()
            elif action == "star": GroupMessageStar.objects.filter(message=msg, user=request.user_obj).delete()
            else: return response(False, "Unknown group message action.", status=400)
            return response(True, "Group message action removed.", {"message": group_message_payload(msg, request.user_obj)})
        except Exception as exc: return response(False, str(exc), status=403)

@method_decorator(csrf_exempt, name="dispatch")
class GroupSearchMediaView(AuthenticatedView):
    def get(self, request, group_id, kind):
        try:
            group = Group.objects.get(id=group_id)
            if kind == "search":
                q = request.GET.get("q", ""); qs = group_message_queryset(request.user_obj, group).filter(Q(text__icontains=q) | Q(attachments__file_name__icontains=q)).distinct().order_by("-created_at")
                return response(True, "Group search loaded.", page(request, qs, lambda m: group_message_payload(m, request.user_obj)))
            ids = group_message_queryset(request.user_obj, group).values_list("id", flat=True); qs = GroupMessageAttachment.objects.filter(message_id__in=ids).select_related("message", "message__sender").order_by("-created_at")
            return response(True, "Group shared media loaded.", page(request, qs, lambda a: {"message_id": str(a.message_id), "kind": a.kind, "file_name": a.file_name, "url": a.file.url if a.file else "", "file_size": a.file_size, "created_at": a.created_at.isoformat()}))
        except Exception as exc: return response(False, str(exc), status=403)


@method_decorator(csrf_exempt, name="dispatch")
class GroupInvitationView(AuthenticatedView):
    def get(self, request, group_id):
        group = Group.objects.get(id=group_id); require_permission(group, request.user_obj, "who_can_create_invites"); qs = GroupInvitation.objects.filter(group=group, revoked_at__isnull=True).order_by("-created_at")
        return response(True, "Invitations loaded.", page(request, qs, lambda i: {"id": str(i.id), "token_preview": i.token_preview, "expires_at": i.expires_at.isoformat() if i.expires_at else None, "max_uses": i.max_uses, "use_count": i.use_count, "created_at": i.created_at.isoformat()}))
    def post(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id); payload = body(request); token, invite = create_invitation(group, request.user_obj, payload.get("expires_hours", 24), payload.get("max_uses"))
            return response(True, "Invitation created.", {"invitation_id": str(invite.id), "token": token, "expires_at": invite.expires_at.isoformat() if invite.expires_at else None}, status=201)
        except Exception as exc: return response(False, str(exc), status=403)
    def delete(self, request, group_id, invitation_id):
        group = Group.objects.get(id=group_id); require_permission(group, request.user_obj, "who_can_create_invites"); GroupInvitation.objects.filter(group=group, id=invitation_id).update(revoked_at=timezone.now()); audit(group, request.user_obj, "invitation_revoked", invitation_id); return response(True, "Invitation revoked.")


@method_decorator(csrf_exempt, name="dispatch")
class GroupInvitationJoinView(AuthenticatedView):
    def post(self, request, token):
        try:
            group, obj, joined = join_by_invitation(request.user_obj, token)
            return response(True, "Invitation processed.", {"group": group_payload(group, request.user_obj), "joined": joined, "request_id": str(getattr(obj, "id", ""))})
        except Exception as exc: return response(False, str(exc), status=403)


@method_decorator(csrf_exempt, name="dispatch")
class GroupJoinRequestView(AuthenticatedView):
    def get(self, request, group_id):
        group = Group.objects.get(id=group_id); require_permission(group, request.user_obj, "who_can_approve_members"); qs = GroupJoinRequest.objects.filter(group=group, status=GroupJoinRequest.STATUS_PENDING).select_related("requester").order_by("-created_at")
        return response(True, "Join requests loaded.", page(request, qs, lambda r: {"id": str(r.id), "requester": compact_user(r.requester, request.user_obj), "message": r.message, "created_at": r.created_at.isoformat()}))
    def post(self, request, group_id, request_id=None, action=None):
        try:
            group = Group.objects.get(id=group_id)
            if request_id:
                require_permission(group, request.user_obj, "who_can_approve_members"); req = GroupJoinRequest.objects.get(id=request_id, group=group, status=GroupJoinRequest.STATUS_PENDING); req.status = GroupJoinRequest.STATUS_APPROVED if action == "approve" else GroupJoinRequest.STATUS_REJECTED; req.decided_by = request.user_obj; req.decided_at = timezone.now(); req.save()
                if action == "approve": add_group_member(group, request.user_obj, req.requester, notify=True)
                create_in_app_notification(req.requester, request.user_obj, f"group_join_{req.status}", f"Your request to join {group.name} was {req.status}.", "group", group.id, {"group_id": str(group.id)})
                return response(True, "Join request updated.", {"status": req.status})
            if GroupBan.objects.filter(group=group, user=request.user_obj, revoked_at__isnull=True).exists(): return response(False, "Banned users cannot request to join.", status=403)
            req, _ = GroupJoinRequest.objects.get_or_create(group=group, requester=request.user_obj, status=GroupJoinRequest.STATUS_PENDING, defaults={"message": body(request).get("message", "")[:280]})
            return response(True, "Join request submitted.", {"request_id": str(req.id)}, status=201)
        except Exception as exc: return response(False, str(exc), status=403)


@method_decorator(csrf_exempt, name="dispatch")
class NotificationView(AuthenticatedView):
    def get(self, request):
        qs = Notification.objects.filter(recipient=request.user_obj).order_by("-created_at"); cursor = request.GET.get("cursor")
        if cursor:
            parsed = parse_datetime(cursor.replace(" ", "+")) or parse_datetime(cursor)
            if parsed: qs = qs.filter(created_at__lt=parsed)
        return response(True, "Notifications loaded.", page(request, qs, lambda n: {"id": str(n.uuid), "type": n.notification_type, "message": n.message, "payload": n.safe_payload, "is_read": n.is_read, "read_at": n.read_at.isoformat() if n.read_at else None, "seen_at": n.seen_at.isoformat() if n.seen_at else None, "created_at": n.created_at.isoformat()}))
    def post(self, request, notification_id=None, action=None):
        qs = Notification.objects.filter(recipient=request.user_obj); now = timezone.now()
        if action == "read-all": qs.update(is_read=True, read_at=now); return response(True, "Notifications marked read.")
        item = qs.get(uuid=notification_id)
        if action == "read": item.is_read = True; item.read_at = now
        elif action == "seen": item.seen_at = now
        else: return response(False, "Unknown notification action.", status=400)
        item.save(update_fields=["is_read", "read_at", "seen_at"]); return response(True, "Notification updated.")
    def delete(self, request, notification_id, action=None): Notification.objects.filter(recipient=request.user_obj, uuid=notification_id).delete(); return response(True, "Notification removed.")


@method_decorator(csrf_exempt, name="dispatch")
class NotificationPreferenceView(AuthenticatedView):
    def get(self, request): pref, _ = NotificationPreference.objects.get_or_create(user=request.user_obj); return response(True, "Notification preferences loaded.", {"preferences": preference_payload(pref)})
    def patch(self, request):
        pref, _ = NotificationPreference.objects.get_or_create(user=request.user_obj); payload = body(request)
        for field in preference_payload(pref).keys():
            if field in payload and field != "security_alerts": setattr(pref, field, bool(payload[field]))
        pref.security_alerts = True; pref.save(); return response(True, "Notification preferences updated.", {"preferences": preference_payload(pref)})

def preference_payload(pref):
    return {field: getattr(pref, field) for field in ["private_messages", "message_requests", "group_messages", "group_mentions", "group_role_changes", "incoming_calls", "missed_calls", "declined_calls", "group_calls", "followers", "likes", "comments", "story_reactions", "reel_activity", "security_alerts", "marketing", "push_enabled", "email_enabled", "in_app_enabled", "notification_previews", "sound", "vibration"]}


@method_decorator(csrf_exempt, name="dispatch")
class AdminGroupModerationView(AuthenticatedView):
    def _staff(self, request):
        if not request.user_obj.is_staff: raise PermissionError("Staff access is required.")
    def get(self, request):
        try:
            self._staff(request); kind = request.GET.get("kind", "groups")
            if kind == "group-message-reports": qs = GroupMessageReport.objects.select_related("message", "message__group", "reporter").order_by("-created_at"); return response(True, "Group message reports loaded.", page(request, qs, lambda r: {"id": r.id, "group_id": str(r.message.group_id), "message_id": str(r.message_id), "reporter": compact_user(r.reporter, request.user_obj), "reason": r.reason, "status": r.status, "context_snapshot": r.context_snapshot}))
            if kind == "group-reports": qs = GroupReport.objects.select_related("group", "reporter").order_by("-created_at"); return response(True, "Group reports loaded.", page(request, qs, lambda r: {"id": r.id, "group_id": str(r.group_id), "group_name": r.group.name, "reporter": compact_user(r.reporter, request.user_obj), "reason": r.reason, "status": r.status, "context_snapshot": r.context_snapshot}))
            qs = Group.objects.all().order_by("-created_at")
            if request.GET.get("status"): qs = qs.filter(status=request.GET["status"])
            if request.GET.get("privacy"): qs = qs.filter(privacy=request.GET["privacy"])
            if request.GET.get("q"): qs = qs.filter(name__icontains=request.GET["q"])
            return response(True, "Admin groups loaded.", page(request, qs, lambda g: group_payload(g, request.user_obj)))
        except PermissionError as exc: return response(False, str(exc), status=403)
    def post(self, request, group_id=None, action=None):
        try:
            self._staff(request); payload = body(request)
            if action in {"suspend", "restore", "remove", "warn-owner"}:
                group = Group.objects.get(id=group_id)
                if action == "suspend": group.status = Group.STATUS_SUSPENDED
                elif action == "restore": group.status = Group.STATUS_ACTIVE
                elif action == "remove": group.status = Group.STATUS_DELETED; group.deleted_at = timezone.now()
                elif action == "warn-owner": create_in_app_notification(group.owner, request.user_obj, "admin_warning", payload.get("message", "Admin warning"), "group", group.id, {"group_id": str(group.id)}, priority="security")
                group.save(); AdminAuditLog.objects.create(admin_user=request.user_obj, action=f"group_{action}", target=str(group.id), reason=payload.get("reason", "")); return response(True, "Group moderation updated.", {"group": group_payload(group, request.user_obj)})
            if action == "announcement":
                ann = AdminAnnouncement.objects.create(title=payload.get("title", "Announcement")[:120], body=payload.get("body", "")[:1000], created_by=request.user_obj, target=payload.get("target", "all"), payload=payload.get("payload", {}), status=AdminAnnouncement.STATUS_SENT, sent_at=timezone.now())
                for user in get_user_model().objects.filter(is_active=True, is_email_verified=True)[:500]: create_in_app_notification(user, request.user_obj, "system_announcement", ann.title, "announcement", ann.id, {"body": ann.body})
                return response(True, "Announcement sent.", {"announcement_id": ann.id})
            return response(False, "Unknown admin group action.", status=400)
        except Exception as exc: return response(False, str(exc), status=403)
