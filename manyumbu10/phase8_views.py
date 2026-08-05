from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import AccountDeletionRequest, DataExportRequest
from .phase8_services import cancel_account_deletion_request, check_rate_limit, create_account_deletion_request, create_data_export_request, data_export_payload, deletion_payload
from .profile_views import AuthenticatedView, page
from .views import body, response


@method_decorator(csrf_exempt, name="dispatch")
class DataExportView(AuthenticatedView):
    def get(self, request):
        qs = DataExportRequest.objects.filter(user=request.user_obj).order_by("-created_at")
        return response(True, "Data export requests loaded.", page(request, qs, data_export_payload))
    def post(self, request):
        try:
            check_rate_limit(request.user_obj, "data_export", 3, 86400)
            payload = body(request)
            item, created = create_data_export_request(request.user_obj, payload.get("scope"), bool(payload.get("recent_auth_confirmed")))
            return response(True, "Data export requested." if created else "Active data export already exists.", {"export": data_export_payload(item)}, status=201 if created else 200)
        except Exception as exc:
            return response(False, str(exc), status=403 if isinstance(exc, PermissionError) else 400)


@method_decorator(csrf_exempt, name="dispatch")
class AccountDeletionView(AuthenticatedView):
    def get(self, request):
        item = AccountDeletionRequest.objects.filter(user=request.user_obj).order_by("-created_at").first()
        return response(True, "Account deletion request loaded.", {"deletion_request": deletion_payload(item) if item else None})
    def post(self, request):
        try:
            payload = body(request)
            item, created = create_account_deletion_request(request.user_obj, payload.get("reason", ""), bool(payload.get("recent_auth_confirmed")))
            return response(True, "Account deletion requested." if created else "Active deletion request already exists.", {"deletion_request": deletion_payload(item)}, status=201 if created else 200)
        except Exception as exc:
            return response(False, str(exc), status=403 if isinstance(exc, PermissionError) else 400)
    def delete(self, request):
        item = cancel_account_deletion_request(request.user_obj)
        return response(True, "Account deletion cancelled." if item else "No active deletion request was found.", {"deletion_request": deletion_payload(item) if item else None})
