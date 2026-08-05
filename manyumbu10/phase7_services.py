from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from .group_services import active_member, create_in_app_notification, has_role, permission_required
from .messaging_services import ensure_membership, messaging_privacy_allows, other_participant
from .models import (
    AppealAttachment, AppealDecision, AudienceInsight, BusinessContactAction, BusinessProfile, Call, CallDeviceSession,
    CallHistory, CallModerationAction, CallParticipant, CallReport, CallSignalEvent, ContentInsight, Conversation,
    ConversationParticipant, CreatorProfile, Follow, Group, GroupBan, GroupMember, MessageReport, ModerationAction, ModerationAppeal,
    ModerationEvidenceAccess, NotificationPreference, ProfessionalAccount, ProfessionalInsightDaily, UserFeatureRestriction,
    VerificationDocument, VerificationRequest,
)
from .profile_views import compact_user
from .services import ensure_profile_records, users_blocked_between

CALL_TIMEOUT_SECONDS = 45
SIGNAL_EVENTS = {"call.ring", "call.offer", "call.answer", "call.ice_candidate", "call.mute_updated", "call.camera_updated", "call.heartbeat"}
TERMINAL_STATUSES = {Call.STATUS_DECLINED, Call.STATUS_MISSED, Call.STATUS_FAILED, Call.STATUS_ENDED, Call.STATUS_CANCELLED}


def active_restriction(user, feature):
    now = timezone.now()
    qs = UserFeatureRestriction.objects.filter(user=user, feature=feature, status=UserFeatureRestriction.STATUS_ACTIVE, starts_at__lte=now).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
    return qs.first()


def require_not_restricted(user, feature):
    restriction = active_restriction(user, feature)
    if restriction:
        raise PermissionError(f"This account is restricted from {feature.replace('_', ' ')}.")
    return True


def private_call_allowed(actor, target, call_type, conversation=None):
    ensure_profile_records(actor); ensure_profile_records(target)
    require_not_restricted(actor, UserFeatureRestriction.FEATURE_START_CALL)
    require_not_restricted(target, UserFeatureRestriction.FEATURE_RECEIVE_CALL)
    if actor == target:
        raise ValueError("You cannot call yourself.")
    if not actor.is_active or not target.is_active or not target.is_email_verified:
        raise PermissionError("This user cannot receive calls.")
    if users_blocked_between(actor, target):
        raise PermissionError("Calling is blocked between these users.")
    privacy = target.privacy_settings
    if call_type == Call.TYPE_PRIVATE_VOICE and not privacy.allow_voice_calls:
        raise PermissionError("This user does not allow voice calls.")
    if call_type == Call.TYPE_PRIVATE_VIDEO and not privacy.allow_video_calls:
        raise PermissionError("This user does not allow video calls.")
    allowed, requires_request = messaging_privacy_allows(actor, target)
    if not allowed:
        raise PermissionError("This user does not allow calls from you.")
    setting = privacy.who_can_call_me
    if setting == "no_one":
        raise PermissionError("This user does not allow calls.")
    if setting == "people_i_follow" and not Follow.objects.filter(follower=target, following=actor).exists():
        raise PermissionError("Only people this user follows may call them.")
    if setting == "mutual_followers" and not (Follow.objects.filter(follower=actor, following=target).exists() and Follow.objects.filter(follower=target, following=actor).exists()):
        raise PermissionError("Only mutual followers may call this user.")
    if setting == "accepted_conversations_only":
        if not conversation:
            raise PermissionError("Accepted conversation is required for calling.")
        try:
            ensure_membership(conversation, actor); ensure_membership(conversation, target)
        except PermissionError:
            raise PermissionError("Accepted conversation is required for calling.")
        if hasattr(conversation, "message_request") and conversation.message_request.status != "accepted":
            raise PermissionError("Accepted conversation is required for calling.")
    if requires_request:
        raise PermissionError("Accept the message request before calling.")
    if privacy.silence_calls_from_unknown_users and not Follow.objects.filter(follower=target, following=actor).exists():
        return "silenced"
    return "allowed"


def group_call_allowed(actor, group, call_type):
    require_not_restricted(actor, UserFeatureRestriction.FEATURE_START_CALL)
    member = active_member(group, actor)
    if not member or GroupBan.objects.filter(group=group, user=actor, revoked_at__isnull=True).exists():
        raise PermissionError("Active group membership is required for calls.")
    settings_obj = getattr(group, "settings", None)
    if call_type == Call.TYPE_GROUP_VOICE and settings_obj and not settings_obj.voice_calls_enabled:
        raise PermissionError("Voice calls are disabled for this group.")
    if call_type == Call.TYPE_GROUP_VIDEO and settings_obj and not settings_obj.video_calls_enabled:
        raise PermissionError("Video calls are disabled for this group.")
    required = permission_required(settings_obj.who_can_start_calls if settings_obj else Group.PERM_ADMINS)
    if not has_role(member, required):
        raise PermissionError("Your group role cannot start calls.")
    return member


def participant_payload(participant, viewer):
    return {"user": compact_user(participant.user, viewer), "role": participant.role, "join_status": participant.join_status, "joined_at": participant.joined_at.isoformat() if participant.joined_at else None, "left_at": participant.left_at.isoformat() if participant.left_at else None, "device_identifier": participant.device_identifier, "is_muted": participant.is_muted, "camera_enabled": participant.camera_enabled, "screen_share_enabled": participant.screen_share_enabled, "connection_quality": participant.connection_quality}


def call_payload(call, viewer):
    participants = [participant_payload(p, viewer) for p in call.participants.select_related("user").all()]
    peer = None
    if call.conversation_id:
        peer = other_participant(call.conversation, viewer)
    return {"id": str(call.id), "call_type": call.call_type, "conversation_id": str(call.conversation_id) if call.conversation_id else None, "group_id": str(call.group_id) if call.group_id else None, "group_name": call.group.name if call.group_id else "", "peer": compact_user(peer, viewer) if peer else None, "initiator": compact_user(call.initiator, viewer), "status": call.status, "participants": participants, "started_at": call.started_at.isoformat() if call.started_at else None, "answered_at": call.answered_at.isoformat() if call.answered_at else None, "ended_at": call.ended_at.isoformat() if call.ended_at else None, "duration_seconds": call.duration_seconds, "failure_reason": call.failure_reason, "provider": call.provider, "signaling": public_call_config(), "created_at": call.created_at.isoformat(), "updated_at": call.updated_at.isoformat()}


def public_call_config():
    return {"media_transport": "webrtc", "stun_servers": getattr(settings, "MANYUMBU_STUN_SERVERS", []), "turn_configured": bool(getattr(settings, "MANYUMBU_TURN_SERVER", "") and getattr(settings, "MANYUMBU_TURN_USERNAME", "") and getattr(settings, "MANYUMBU_TURN_PASSWORD", "")), "provider_fallback": getattr(settings, "MANYUMBU_CALL_PROVIDER", "none"), "native_webrtc_required": True, "expo_go_supported": False}


def participant_users_for_call(call):
    return [p.user for p in call.participants.select_related("user")]


def any_active_call(user):
    return CallParticipant.objects.filter(user=user, call__status__in=[Call.STATUS_RINGING, Call.STATUS_CONNECTING, Call.STATUS_ACTIVE, Call.STATUS_RECONNECTING], join_status__in=[CallParticipant.STATUS_INVITED, CallParticipant.STATUS_RINGING, CallParticipant.STATUS_JOINED]).select_related("call").first()


@transaction.atomic
def create_call(actor, payload):
    call_type = payload.get("call_type", Call.TYPE_PRIVATE_VOICE)
    if call_type not in dict(Call.TYPES):
        raise ValueError("Unknown call type.")
    existing = any_active_call(actor)
    if existing:
        raise PermissionError("You are already in an active call.")
    conversation = None; group = None; targets = []
    if call_type in {Call.TYPE_PRIVATE_VOICE, Call.TYPE_PRIVATE_VIDEO}:
        conversation = Conversation.objects.get(id=payload.get("conversation_id"))
        ensure_membership(conversation, actor)
        target = other_participant(conversation, actor)
        if not target:
            raise ValueError("Private call target was not found.")
        privacy_state = private_call_allowed(actor, target, call_type, conversation)
        if any_active_call(target):
            call = Call.objects.create(call_type=call_type, conversation=conversation, initiator=actor, status=Call.STATUS_BUSY, failure_reason="Target user is busy.")
            CallParticipant.objects.create(call=call, user=actor, role=CallParticipant.ROLE_HOST, join_status=CallParticipant.STATUS_LEFT)
            CallParticipant.objects.create(call=call, user=target, role=CallParticipant.ROLE_INVITEE, join_status=CallParticipant.STATUS_BUSY)
            create_history(call)
            create_in_app_notification(actor, target, "call_busy", f"{target.username} is busy.", "call", call.id, {"call_id": str(call.id)})
            return call
        targets = [target]
    else:
        group = Group.objects.get(id=payload.get("group_id"))
        group_call_allowed(actor, group, call_type)
        settings_obj = getattr(group, "settings", None)
        active_count = GroupMember.objects.filter(group=group, status=GroupMember.STATUS_ACTIVE).count()
        max_participants = settings_obj.maximum_call_participants if settings_obj else 16
        if active_count > max_participants:
            raise PermissionError("This group has too many members for a call.")
        targets = [m.user for m in GroupMember.objects.filter(group=group, status=GroupMember.STATUS_ACTIVE).exclude(user=actor).select_related("user")[:max_participants - 1]]
        privacy_state = "allowed"
    call = Call.objects.create(call_type=call_type, conversation=conversation, group=group, initiator=actor, status=Call.STATUS_RINGING, started_at=timezone.now(), signaling_metadata={"privacy_state": privacy_state, "timeout_seconds": CALL_TIMEOUT_SECONDS})
    CallParticipant.objects.create(call=call, user=actor, role=CallParticipant.ROLE_HOST, join_status=CallParticipant.STATUS_JOINED, joined_at=timezone.now(), camera_enabled="video" in call_type)
    for target in targets:
        participant_status = CallParticipant.STATUS_RINGING
        CallParticipant.objects.create(call=call, user=target, role=CallParticipant.ROLE_INVITEE if conversation else CallParticipant.ROLE_MEMBER, join_status=participant_status, camera_enabled=False)
        notify_call_target(call, actor, target)
    create_history(call)
    return call


def notify_call_target(call, actor, target):
    prefs, _ = NotificationPreference.objects.get_or_create(user=target)
    if not getattr(target.privacy_settings, "show_call_notifications", True):
        return None
    if call.group_id and not prefs.group_calls:
        return None
    if not call.group_id and not prefs.incoming_calls:
        return None
    title = f"Group call started in {call.group.name}" if call.group_id else f"Incoming {'video' if 'video' in call.call_type else 'voice'} call from {actor.username}"
    return create_in_app_notification(target, actor, "incoming_call" if not call.group_id else "group_call_started", title, "call", call.id, {"call_id": str(call.id), "deep_link": f"manyumbu://calls/{call.id}"}, f"call:{call.id}", priority="high")


def create_history(call):
    for participant in call.participants.select_related("user"):
        direction = "outgoing" if participant.user == call.initiator else "incoming"
        CallHistory.objects.get_or_create(call=call, user=participant.user, defaults={"direction": direction})


def require_call_participant(call, user):
    participant = CallParticipant.objects.filter(call=call, user=user).first()
    if not participant:
        raise PermissionError("You are not a participant in this call.")
    if call.group_id and not active_member(call.group, user):
        raise PermissionError("Active group membership is required for this call.")
    return participant


@transaction.atomic
def call_transition(call, user, action, payload=None):
    payload = payload or {}
    participant = require_call_participant(call, user)
    now = timezone.now()
    if action == "accept":
        if call.status in TERMINAL_STATUSES:
            raise PermissionError("This call has ended.")
        call.status = Call.STATUS_ACTIVE; call.answered_at = call.answered_at or now
        participant.join_status = CallParticipant.STATUS_JOINED; participant.joined_at = participant.joined_at or now
        participant.device_identifier = str(payload.get("device_id", ""))[:120]
        participant.camera_enabled = "video" in call.call_type and bool(payload.get("camera_enabled", True))
    elif action == "decline":
        participant.join_status = CallParticipant.STATUS_DECLINED; participant.left_at = now
        if call.participants.exclude(user=user).filter(join_status=CallParticipant.STATUS_JOINED).count() <= 1:
            call.status = Call.STATUS_DECLINED; call.ended_at = now
    elif action == "cancel":
        if call.initiator != user:
            raise PermissionError("Only the initiator can cancel this call.")
        call.status = Call.STATUS_CANCELLED; call.ended_at = now
        call.participants.exclude(user=user).update(join_status=CallParticipant.STATUS_MISSED, left_at=now)
    elif action == "end":
        if call.group_id and participant.role not in {CallParticipant.ROLE_HOST} and payload.get("for_all"):
            raise PermissionError("Only the host can end this call for everyone.")
        if payload.get("for_all") or not call.group_id:
            call.status = Call.STATUS_ENDED; call.ended_at = now; call.participants.filter(left_at__isnull=True).update(join_status=CallParticipant.STATUS_LEFT, left_at=now)
        else:
            participant.join_status = CallParticipant.STATUS_LEFT; participant.left_at = now
            if not call.participants.filter(join_status=CallParticipant.STATUS_JOINED).exclude(user=user).exists():
                call.status = Call.STATUS_ENDED; call.ended_at = now
    elif action == "join":
        if call.status in TERMINAL_STATUSES:
            raise PermissionError("This call has ended.")
        participant.join_status = CallParticipant.STATUS_JOINED; participant.joined_at = participant.joined_at or now; call.status = Call.STATUS_ACTIVE; call.answered_at = call.answered_at or now
    elif action == "leave":
        participant.join_status = CallParticipant.STATUS_LEFT; participant.left_at = now
        if not call.participants.filter(join_status=CallParticipant.STATUS_JOINED).exclude(user=user).exists():
            call.status = Call.STATUS_ENDED; call.ended_at = now
    elif action == "missed-timeout":
        if call.initiator != user:
            raise PermissionError("Only the initiator can timeout this call.")
        call.status = Call.STATUS_MISSED; call.ended_at = now; call.participants.exclude(user=user).update(join_status=CallParticipant.STATUS_MISSED, left_at=now)
    else:
        raise ValueError("Unknown call action.")
    if call.ended_at and call.started_at:
        call.duration_seconds = max(int((call.ended_at - call.started_at).total_seconds()), 0)
    call.save(); participant.save()
    create_history(call)
    notify_call_state(call, action, user)
    return call


def notify_call_state(call, action, actor):
    if action == "missed-timeout": ntype = "missed_call"; message = "Missed call"
    elif action == "decline": ntype = "declined_call"; message = "Call declined"
    elif action == "end" and call.status == Call.STATUS_FAILED: ntype = "call_ended_unexpectedly"; message = "Call ended unexpectedly"
    else: return
    for participant in call.participants.exclude(user=actor).select_related("user"):
        create_in_app_notification(participant.user, actor, ntype, message, "call", call.id, {"call_id": str(call.id)}, f"call:{call.id}:{ntype}")


def list_calls_for(user):
    return Call.objects.filter(participants__user=user, history_items__user=user, history_items__local_deleted_at__isnull=True).distinct().select_related("initiator", "conversation", "group").prefetch_related("participants__user").order_by("-created_at")


def record_signal(call, sender, event_name, payload, request_id=""):
    require_call_participant(call, sender)
    safe_payload = {k: v for k, v in (payload or {}).items() if k not in {"token", "secret", "credential", "password"}}
    if event_name not in SIGNAL_EVENTS:
        raise ValueError("Unknown signaling event.")
    CallSignalEvent.objects.create(call=call, sender=sender, event_name=event_name, request_id=str(request_id or "")[:120], safe_payload=safe_payload)
    return {"call_id": str(call.id), "sender": sender.username, "payload": safe_payload}


def report_call(call, reporter, reason, details=""):
    require_call_participant(call, reporter)
    report, _ = CallReport.objects.get_or_create(call=call, reporter=reporter, reason=reason, defaults={"details": details[:1000], "context_snapshot": {"call_id": str(call.id), "call_type": call.call_type, "status": call.status, "participants": [p.user.username for p in call.participants.select_related("user")], "signals": [e.event_name for e in call.signal_events.order_by("-created_at")[:10]]}})
    return report


def moderation_action_payload(action):
    return {"id": str(action.id), "target_user": compact_user(action.target_user), "moderator": compact_user(action.moderator) if action.moderator else None, "action_type": action.action_type, "status": action.status, "reason": action.reason, "object_type": action.object_type, "object_id": action.object_id, "appeal_eligible": action.appeal_eligible, "expires_at": action.expires_at.isoformat() if action.expires_at else None, "created_at": action.created_at.isoformat()}


def restriction_payload(restriction):
    return {"id": restriction.id, "feature": restriction.feature, "reason": restriction.reason, "starts_at": restriction.starts_at.isoformat(), "expires_at": restriction.expires_at.isoformat() if restriction.expires_at else None, "status": restriction.status, "appeal_eligible": restriction.appeal_eligible}


def create_feature_restriction(user, moderator, payload):
    feature = payload.get("feature")
    if feature not in dict(UserFeatureRestriction.FEATURES):
        raise ValueError("Unknown feature restriction.")
    hours = payload.get("hours")
    expires = timezone.now() + timedelta(hours=int(hours)) if hours else None
    restriction = UserFeatureRestriction.objects.create(user=user, moderator=moderator, feature=feature, reason=str(payload.get("reason", "Policy violation"))[:280], expires_at=expires, appeal_eligible=bool(payload.get("appeal_eligible", True)))
    action = ModerationAction.objects.create(target_user=user, moderator=moderator, action_type=ModerationAction.ACTION_FEATURE_RESTRICTION, status=ModerationAction.STATUS_ACTION_TAKEN, reason=restriction.reason, object_type="user_feature_restriction", object_id=str(restriction.id), appeal_eligible=restriction.appeal_eligible, expires_at=expires)
    return restriction, action


def appeal_payload(appeal):
    return {"id": str(appeal.id), "action": moderation_action_payload(appeal.action), "explanation": appeal.explanation, "status": appeal.status, "created_at": appeal.created_at.isoformat(), "decision": {"decision": appeal.decision.decision, "notes": appeal.decision.notes} if hasattr(appeal, "decision") else None}


def create_appeal(user, action, explanation, files=None):
    if action.target_user != user or not action.appeal_eligible:
        raise PermissionError("This moderation action cannot be appealed.")
    if ModerationAppeal.objects.filter(action=action, user=user, status__in=ModerationAppeal.ACTIVE_STATUSES).exists():
        raise ValueError("An active appeal already exists for this action.")
    appeal = ModerationAppeal.objects.create(action=action, user=user, explanation=str(explanation or "")[:2000])
    for upload in files or []:
        AppealAttachment.objects.create(appeal=appeal, file=upload, file_name=getattr(upload, "name", "attachment")[:180], mime_type=getattr(upload, "content_type", "application/octet-stream")[:120], file_size=getattr(upload, "size", 0) or 0)
    return appeal


def decide_appeal(appeal, reviewer, decision, notes=""):
    if decision not in {ModerationAppeal.STATUS_APPROVED, ModerationAppeal.STATUS_PARTIALLY_APPROVED, ModerationAppeal.STATUS_REJECTED}:
        raise ValueError("Invalid appeal decision.")
    appeal.status = decision; appeal.save(update_fields=["status", "updated_at"])
    AppealDecision.objects.update_or_create(appeal=appeal, defaults={"reviewer": reviewer, "decision": decision, "notes": notes[:2000]})
    if decision in {ModerationAppeal.STATUS_APPROVED, ModerationAppeal.STATUS_PARTIALLY_APPROVED}:
        appeal.action.status = ModerationAction.STATUS_RESOLVED; appeal.action.save(update_fields=["status", "updated_at"])
    create_in_app_notification(appeal.user, reviewer, "appeal_decision", f"Your appeal was {decision.replace('_', ' ')}.", "moderation_appeal", appeal.id, {"appeal_id": str(appeal.id)}, priority="security")
    return appeal


def eligible_for_professional(user):
    ensure_profile_records(user)
    if not user.is_active or not user.is_email_verified:
        raise PermissionError("Verified active account is required.")
    if active_restriction(user, UserFeatureRestriction.FEATURE_PROFESSIONAL):
        raise PermissionError("Professional features are restricted for this account.")
    return True


def professional_payload(account):
    data = {"account_type": account.account_type, "status": account.status, "category": account.category, "public_contact_enabled": account.public_contact_enabled, "created_at": account.created_at.isoformat(), "updated_at": account.updated_at.isoformat()}
    if hasattr(account, "creator_profile"):
        p = account.creator_profile; data["creator"] = {"creator_category": p.creator_category, "professional_bio": p.professional_bio, "collaboration_email": p.collaboration_email, "public_contact": p.public_contact, "collaboration_enabled": p.collaboration_enabled}
    if hasattr(account, "business_profile"):
        p = account.business_profile; data["business"] = {"business_name": p.business_name, "business_category": p.business_category, "description": p.description, "website": p.website, "email": p.email, "show_phone_number": p.show_phone_number, "public_phone_number": p.public_phone_number if p.show_phone_number else "", "physical_location": p.physical_location, "business_hours": p.business_hours, "contact_buttons": p.contact_buttons}
    return data


def create_creator_account(user, payload):
    eligible_for_professional(user)
    account, _ = ProfessionalAccount.objects.update_or_create(user=user, defaults={"account_type": ProfessionalAccount.TYPE_CREATOR, "category": payload.get("creator_category", payload.get("category", "creator"))[:80], "public_contact_enabled": bool(payload.get("public_contact_enabled", False)), "status": ProfessionalAccount.STATUS_ACTIVE})
    CreatorProfile.objects.update_or_create(professional_account=account, defaults={"creator_category": payload.get("creator_category", account.category)[:80], "professional_bio": payload.get("professional_bio", "")[:280], "collaboration_email": payload.get("collaboration_email", ""), "public_contact": payload.get("public_contact", "")[:120], "collaboration_enabled": bool(payload.get("collaboration_enabled", False))})
    user.is_creator = True; user.is_business = False; user.profile.account_type = "creator"; user.save(update_fields=["is_creator", "is_business", "updated_at"]); user.profile.save(update_fields=["account_type", "updated_at"])
    return account


def create_business_account(user, payload):
    eligible_for_professional(user)
    account, _ = ProfessionalAccount.objects.update_or_create(user=user, defaults={"account_type": ProfessionalAccount.TYPE_BUSINESS, "category": payload.get("business_category", payload.get("category", "business"))[:80], "public_contact_enabled": bool(payload.get("public_contact_enabled", True)), "status": ProfessionalAccount.STATUS_ACTIVE})
    BusinessProfile.objects.update_or_create(professional_account=account, defaults={"business_name": payload.get("business_name", user.full_name)[:120], "business_category": payload.get("business_category", account.category)[:80], "description": payload.get("description", "")[:1000], "website": payload.get("website", ""), "email": payload.get("email", ""), "show_phone_number": bool(payload.get("show_phone_number", False)), "public_phone_number": payload.get("public_phone_number", user.phone_number)[:20], "physical_location": payload.get("physical_location", "")[:180], "business_hours": payload.get("business_hours", {}), "contact_buttons": payload.get("contact_buttons", [])})
    user.is_business = True; user.is_creator = False; user.profile.account_type = "business"; user.save(update_fields=["is_business", "is_creator", "updated_at"]); user.profile.save(update_fields=["account_type", "updated_at"])
    return account


def insight_payload(account):
    totals = account.daily_insights.aggregate(profile_views=Sum("profile_views"), follower_growth=Sum("follower_growth"), post_impressions=Sum("post_impressions"), post_reach=Sum("post_reach"), post_engagement=Sum("post_engagement"), reel_views=Sum("reel_views"), reel_watch_time_seconds=Sum("reel_watch_time_seconds"), story_views=Sum("story_views"), saves=Sum("saves"), shares=Sum("shares"), comments=Sum("comments"), message_response_count=Sum("message_response_count"))
    return {key: value or 0 for key, value in totals.items()} | {"definitions": {"reach": "Approximate unique accounts reached.", "engagement": "Likes, comments, saves, shares, and replies.", "delay": "Insights may be delayed or approximate."}}


def create_verification_request(user, payload, files=None):
    eligible_for_professional(user)
    request = VerificationRequest.objects.create(user=user, account_type=payload.get("account_type", ProfessionalAccount.TYPE_CREATOR), public_name=payload.get("public_name", user.full_name)[:120], category=payload.get("category", "")[:80], reason=payload.get("reason", "")[:2000], supporting_links=payload.get("supporting_links", []), status=VerificationRequest.STATUS_SUBMITTED)
    for upload in files or []:
        VerificationDocument.objects.create(request=request, file=upload, file_name=getattr(upload, "name", "document")[:180], mime_type=getattr(upload, "content_type", "application/octet-stream")[:120], file_size=getattr(upload, "size", 0) or 0)
    return request


def verification_payload(request, include_private=False):
    data = {"id": str(request.id), "account_type": request.account_type, "public_name": request.public_name, "category": request.category, "reason": request.reason, "supporting_links": request.supporting_links, "status": request.status, "created_at": request.created_at.isoformat(), "updated_at": request.updated_at.isoformat()}
    if include_private:
        data["documents"] = [{"id": d.id, "file_name": d.file_name, "mime_type": d.mime_type, "file_size": d.file_size} for d in request.documents.all()]
    return data


def admin_queue_items():
    items = []
    for report in CallReport.objects.select_related("call", "reporter").filter(status=MessageReport.STATUS_PENDING).order_by("-created_at")[:50]:
        items.append({"kind": "call_report", "id": report.id, "reason": report.reason, "status": report.status, "reporter": compact_user(report.reporter), "object_id": str(report.call_id), "created_at": report.created_at.isoformat()})
    for appeal in ModerationAppeal.objects.select_related("user", "action").filter(status__in=ModerationAppeal.ACTIVE_STATUSES).order_by("-created_at")[:50]:
        items.append({"kind": "appeal", "id": str(appeal.id), "reason": appeal.action.reason, "status": appeal.status, "reporter": compact_user(appeal.user), "object_id": str(appeal.action_id), "created_at": appeal.created_at.isoformat()})
    for request in VerificationRequest.objects.select_related("user").filter(status__in=[VerificationRequest.STATUS_SUBMITTED, VerificationRequest.STATUS_UNDER_REVIEW]).order_by("-created_at")[:50]:
        items.append({"kind": "verification_request", "id": str(request.id), "reason": request.reason[:120], "status": request.status, "reporter": compact_user(request.user), "object_id": str(request.id), "created_at": request.created_at.isoformat()})
    return sorted(items, key=lambda row: row["created_at"], reverse=True)
