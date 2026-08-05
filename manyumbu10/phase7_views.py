import json

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import Call, CallHistory, CallReport, ModerationAction, ModerationAppeal, ProfessionalAccount, UserFeatureRestriction, VerificationRequest
from .phase7_services import admin_queue_items, appeal_payload, call_payload, call_transition, create_appeal, create_business_account, create_call, create_creator_account, create_feature_restriction, create_verification_request, decide_appeal, insight_payload, moderation_action_payload, professional_payload, public_call_config, report_call, require_call_participant, restriction_payload, verification_payload
from .profile_views import AuthenticatedView, compact_user, get_target, page, privacy_payload
from .views import body, response


def parse_payload(request):
    if request.content_type and request.content_type.startswith("multipart/"):
        payload = request.POST.dict()
        for key in ["supporting_links", "business_hours", "contact_buttons", "payload"]:
            if key in payload:
                try: payload[key] = json.loads(payload[key])
                except Exception: payload[key] = [] if key in {"supporting_links", "contact_buttons"} else {}
        return payload
    return body(request)


@method_decorator(csrf_exempt, name="dispatch")
class CallListView(AuthenticatedView):
    def get(self, request):
        from .phase7_services import list_calls_for
        qs = list_calls_for(request.user_obj)
        if request.GET.get("status"): qs = qs.filter(status=request.GET["status"])
        if request.GET.get("type"): qs = qs.filter(call_type=request.GET["type"])
        return response(True, "Calls loaded.", page(request, qs, lambda call: call_payload(call, request.user_obj), default_size=30))

    def post(self, request):
        try:
            call = create_call(request.user_obj, parse_payload(request))
            return response(True, "Call created.", {"call": call_payload(call, request.user_obj)}, status=201)
        except Exception as exc:
            return response(False, str(exc), status=403 if isinstance(exc, PermissionError) else 400)


@method_decorator(csrf_exempt, name="dispatch")
class CallDetailView(AuthenticatedView):
    def get(self, request, call_id):
        try:
            call = Call.objects.select_related("initiator", "conversation", "group").prefetch_related("participants__user").get(id=call_id)
            require_call_participant(call, request.user_obj)
            return response(True, "Call loaded.", {"call": call_payload(call, request.user_obj)})
        except Call.DoesNotExist:
            return response(False, "Call was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)


@method_decorator(csrf_exempt, name="dispatch")
class CallActionView(AuthenticatedView):
    def post(self, request, call_id, action):
        try:
            call = Call.objects.get(id=call_id)
            if action == "report":
                payload = parse_payload(request); report = report_call(call, request.user_obj, payload.get("reason", "other"), payload.get("details", ""))
                return response(True, "Call report submitted.", {"report_id": report.id})
            if action == "config":
                require_call_participant(call, request.user_obj)
                return response(True, "Call configuration loaded.", {"config": public_call_config()})
            if action == "timeout": action = "missed-timeout"
            call = call_transition(call, request.user_obj, action, parse_payload(request))
            return response(True, "Call updated.", {"call": call_payload(call, request.user_obj)})
        except Call.DoesNotExist:
            return response(False, "Call was not found.", status=404)
        except Exception as exc:
            return response(False, str(exc), status=403 if isinstance(exc, PermissionError) else 400)


@method_decorator(csrf_exempt, name="dispatch")
class CallHistoryView(AuthenticatedView):
    def delete(self, request, call_id):
        CallHistory.objects.filter(call_id=call_id, user=request.user_obj).update(local_deleted_at=timezone.now())
        return response(True, "Call history item removed locally.")


@method_decorator(csrf_exempt, name="dispatch")
class CallPrivacyView(AuthenticatedView):
    def get(self, request):
        return response(True, "Call privacy loaded.", {"privacy": privacy_payload(request.user_obj.privacy_settings)})
    def patch(self, request):
        payload = body(request); settings = request.user_obj.privacy_settings
        for field in ["who_can_call_me", "allow_voice_calls", "allow_video_calls", "show_call_notifications", "silence_calls_from_unknown_users"]:
            if field in payload: setattr(settings, field, payload[field])
        settings.save()
        return response(True, "Call privacy updated.", {"privacy": privacy_payload(settings)})


@method_decorator(csrf_exempt, name="dispatch")
class ModerationActionView(AuthenticatedView):
    def get(self, request):
        qs = ModerationAction.objects.filter(target_user=request.user_obj).order_by("-created_at")
        return response(True, "Moderation actions loaded.", page(request, qs, moderation_action_payload))


@method_decorator(csrf_exempt, name="dispatch")
class RestrictionView(AuthenticatedView):
    def get(self, request):
        qs = UserFeatureRestriction.objects.filter(user=request.user_obj).order_by("-created_at")
        return response(True, "Feature restrictions loaded.", page(request, qs, restriction_payload))


@method_decorator(csrf_exempt, name="dispatch")
class AppealView(AuthenticatedView):
    def get(self, request):
        qs = ModerationAppeal.objects.filter(user=request.user_obj).select_related("action", "action__target_user", "action__moderator").order_by("-created_at")
        return response(True, "Appeals loaded.", page(request, qs, appeal_payload))
    def post(self, request, action_id=None):
        try:
            action = ModerationAction.objects.get(id=action_id)
            appeal = create_appeal(request.user_obj, action, parse_payload(request).get("explanation", ""), request.FILES.getlist("attachments") if hasattr(request, "FILES") else [])
            return response(True, "Appeal submitted.", {"appeal": appeal_payload(appeal)}, status=201)
        except ModerationAction.DoesNotExist:
            return response(False, "Moderation action was not found.", status=404)
        except Exception as exc:
            return response(False, str(exc), status=403 if isinstance(exc, PermissionError) else 400)


@method_decorator(csrf_exempt, name="dispatch")
class ProfessionalAccountView(AuthenticatedView):
    def get(self, request):
        account = getattr(request.user_obj, "professional_account", None)
        return response(True, "Professional account loaded.", {"professional_account": professional_payload(account) if account else None})
    def patch(self, request):
        account = getattr(request.user_obj, "professional_account", None)
        if not account: return response(False, "Professional account was not found.", status=404)
        payload = body(request)
        for field in ["category", "public_contact_enabled", "dashboard_settings"]:
            if field in payload: setattr(account, field, payload[field])
        account.save(); return response(True, "Professional account updated.", {"professional_account": professional_payload(account)})
    def delete(self, request):
        account = getattr(request.user_obj, "professional_account", None)
        if account:
            account.status = ProfessionalAccount.STATUS_REMOVED; account.save(update_fields=["status", "updated_at"])
            request.user_obj.is_creator = False; request.user_obj.is_business = False; request.user_obj.profile.account_type = "personal"; request.user_obj.save(update_fields=["is_creator", "is_business", "updated_at"]); request.user_obj.profile.save(update_fields=["account_type", "updated_at"])
        return response(True, "Professional account removed.")


@method_decorator(csrf_exempt, name="dispatch")
class CreatorAccountView(AuthenticatedView):
    def post(self, request):
        try:
            account = create_creator_account(request.user_obj, parse_payload(request))
            return response(True, "Creator account enabled.", {"professional_account": professional_payload(account)}, status=201)
        except Exception as exc:
            return response(False, str(exc), status=403 if isinstance(exc, PermissionError) else 400)


@method_decorator(csrf_exempt, name="dispatch")
class BusinessAccountView(AuthenticatedView):
    def post(self, request):
        try:
            account = create_business_account(request.user_obj, parse_payload(request))
            return response(True, "Business account enabled.", {"professional_account": professional_payload(account)}, status=201)
        except Exception as exc:
            return response(False, str(exc), status=403 if isinstance(exc, PermissionError) else 400)


@method_decorator(csrf_exempt, name="dispatch")
class ProfessionalInsightView(AuthenticatedView):
    def get(self, request):
        account = getattr(request.user_obj, "professional_account", None)
        if not account: return response(False, "Professional account is required.", status=403)
        return response(True, "Professional insights loaded.", {"insights": insight_payload(account)})


@method_decorator(csrf_exempt, name="dispatch")
class VerificationRequestView(AuthenticatedView):
    def get(self, request, request_id=None):
        if request_id:
            item = VerificationRequest.objects.get(id=request_id, user=request.user_obj)
            return response(True, "Verification request loaded.", {"verification_request": verification_payload(item, include_private=True)})
        qs = VerificationRequest.objects.filter(user=request.user_obj).order_by("-created_at")
        return response(True, "Verification requests loaded.", page(request, qs, verification_payload))
    def post(self, request):
        try:
            item = create_verification_request(request.user_obj, parse_payload(request), request.FILES.getlist("documents") if hasattr(request, "FILES") else [])
            return response(True, "Verification request submitted.", {"verification_request": verification_payload(item, include_private=True)}, status=201)
        except Exception as exc:
            return response(False, str(exc), status=403 if isinstance(exc, PermissionError) else 400)


@method_decorator(csrf_exempt, name="dispatch")
class AdminPhaseSevenView(AuthenticatedView):
    def _staff(self, request):
        if not request.user_obj.is_staff: raise PermissionError("Staff access is required.")
    def get(self, request, kind=None):
        try:
            self._staff(request); kind = kind or request.GET.get("kind", "queue")
            if kind == "queue": return response(True, "Moderation queue loaded.", {"results": admin_queue_items(), "count": len(admin_queue_items())})
            if kind == "call-reports":
                qs = CallReport.objects.select_related("call", "reporter").order_by("-created_at")
                return response(True, "Call reports loaded.", page(request, qs, lambda r: {"id": r.id, "call_id": str(r.call_id), "reporter": compact_user(r.reporter, request.user_obj), "reason": r.reason, "details": r.details, "status": r.status, "context_snapshot": r.context_snapshot, "created_at": r.created_at.isoformat()}))
            if kind == "appeals":
                qs = ModerationAppeal.objects.select_related("user", "action").order_by("-created_at")
                return response(True, "Appeals loaded.", page(request, qs, appeal_payload))
            if kind == "verification-requests":
                qs = VerificationRequest.objects.select_related("user").prefetch_related("documents").order_by("-created_at")
                return response(True, "Verification requests loaded.", page(request, qs, lambda v: verification_payload(v, include_private=True)))
            if kind == "professional-accounts":
                qs = ProfessionalAccount.objects.select_related("user").order_by("-created_at")
                return response(True, "Professional accounts loaded.", page(request, qs, lambda p: {"user": compact_user(p.user, request.user_obj), **professional_payload(p)}))
            return response(False, "Unknown admin queue kind.", status=404)
        except PermissionError as exc: return response(False, str(exc), status=403)
    def post(self, request, kind=None, object_id=None, action=None, username=None):
        try:
            self._staff(request); payload = body(request); kind = kind or ""
            if kind == "appeals":
                appeal = ModerationAppeal.objects.get(id=object_id); appeal = decide_appeal(appeal, request.user_obj, action, payload.get("notes", "")); return response(True, "Appeal decision saved.", {"appeal": appeal_payload(appeal)})
            if kind == "verification-requests":
                item = VerificationRequest.objects.get(id=object_id); item.status = VerificationRequest.STATUS_APPROVED if action == "approve" else VerificationRequest.STATUS_REJECTED; item.decided_by = request.user_obj; item.decided_at = timezone.now(); item.internal_notes = payload.get("notes", "")[:2000]; item.save();
                if item.status == VerificationRequest.STATUS_APPROVED: item.user.is_verified = True; item.user.save(update_fields=["is_verified", "updated_at"])
                return response(True, "Verification request updated.", {"verification_request": verification_payload(item, include_private=True)})
            if kind == "users" and action == "restrictions":
                target = get_target(username); restriction, moderation_action = create_feature_restriction(target, request.user_obj, payload); return response(True, "Restriction created.", {"restriction": restriction_payload(restriction), "moderation_action": moderation_action_payload(moderation_action)}, status=201)
            if kind == "professional-accounts":
                target = get_target(username); account = target.professional_account
                if action == "remove-creator": target.is_creator = False; account.status = ProfessionalAccount.STATUS_REMOVED
                elif action == "remove-business": target.is_business = False; account.status = ProfessionalAccount.STATUS_REMOVED
                elif action == "remove-verification": target.is_verified = False
                else: return response(False, "Unknown professional action.", status=400)
                target.save(); account.save(); return response(True, "Professional account action saved.")
            return response(False, "Unknown admin action.", status=400)
        except Exception as exc: return response(False, str(exc), status=403 if isinstance(exc, PermissionError) else 400)
    def delete(self, request, kind=None, username=None, object_id=None):
        try:
            self._staff(request)
            if kind == "users":
                target = get_target(username); UserFeatureRestriction.objects.filter(id=object_id, user=target).update(status=UserFeatureRestriction.STATUS_REVOKED, updated_at=timezone.now()); return response(True, "Restriction revoked.")
            return response(False, "Unknown admin action.", status=400)
        except Exception as exc: return response(False, str(exc), status=403 if isinstance(exc, PermissionError) else 400)
