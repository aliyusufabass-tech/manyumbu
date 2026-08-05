from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

from .models import AccountDeletionRequest, DataExportRequest, OperationalEvent, UserSession
from .services import hash_token

DEFAULT_EXPORT_SCOPE = ["profile", "posts", "comments", "stories", "reels", "relationships", "messages", "groups", "notifications", "call_history", "moderation", "professional_account"]
SENSITIVE_LOG_KEYS = {"password", "token", "secret", "credential", "authorization", "turn_password", "email_password"}


def sanitize_metadata(value):
    if isinstance(value, dict):
        return {k: ("[redacted]" if k.lower() in SENSITIVE_LOG_KEYS else sanitize_metadata(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_metadata(v) for v in value]
    return value


def record_operational_event(event_type, level="info", actor=None, metadata=None, correlation_id=""):
    return OperationalEvent.objects.create(event_type=event_type[:80], level=level, actor=actor, correlation_id=correlation_id[:80], safe_metadata=sanitize_metadata(metadata or {}))


def rate_limit_key(user, scope):
    return f"rate:{scope}:{getattr(user, 'phone_number', 'anonymous')}"


def check_rate_limit(user, scope, limit=30, window_seconds=60):
    key = rate_limit_key(user, scope)
    current = cache.get(key, 0)
    if current >= limit:
        record_operational_event("rate_limit", "warning", user, {"scope": scope, "limit": limit})
        raise PermissionError("Too many requests. Please try again later.")
    cache.set(key, current + 1, timeout=window_seconds)
    return limit - current - 1


def create_data_export_request(user, scope=None, recent_auth_confirmed=False):
    if not recent_auth_confirmed:
        raise PermissionError("Recent authentication is required to request data export.")
    active = DataExportRequest.objects.filter(user=user, status__in=[DataExportRequest.STATUS_REQUESTED, DataExportRequest.STATUS_PROCESSING, DataExportRequest.STATUS_READY], expires_at__gt=timezone.now()).first()
    if active:
        return active, False
    item = DataExportRequest.objects.create(user=user, export_scope=scope or DEFAULT_EXPORT_SCOPE, expires_at=timezone.now() + timedelta(days=7), recent_auth_confirmed_at=timezone.now())
    record_operational_event("data_export_requested", actor=user, metadata={"request_id": str(item.id)})
    return item, True


def data_export_payload(item, include_token=False):
    return {"id": str(item.id), "status": item.status, "export_scope": item.export_scope, "download_available": bool(item.file and item.download_token_hash and item.expires_at and item.expires_at > timezone.now()), "expires_at": item.expires_at.isoformat() if item.expires_at else None, "failure_reason": item.failure_reason, "created_at": item.created_at.isoformat(), "updated_at": item.updated_at.isoformat()}


def mark_export_ready(item, token, file_name=""):
    item.status = DataExportRequest.STATUS_READY
    item.download_token_hash = hash_token(token)
    item.expires_at = timezone.now() + timedelta(days=7)
    item.save(update_fields=["status", "download_token_hash", "expires_at", "updated_at"])
    return item


def create_account_deletion_request(user, reason="", recent_auth_confirmed=False):
    if not recent_auth_confirmed:
        raise PermissionError("Recent authentication is required to request account deletion.")
    active = AccountDeletionRequest.objects.filter(user=user, status=AccountDeletionRequest.STATUS_REQUESTED).first()
    if active:
        return active, False
    item = AccountDeletionRequest.objects.create(user=user, reason=reason[:280], grace_period_ends_at=timezone.now() + timedelta(days=getattr(settings, "MANYUMBU_DELETION_GRACE_DAYS", 30)), retention_notes={"messages": "Private message records may be retained for other participants.", "moderation": "Audit and moderation records may be retained for safety and legal reasons.", "verification_documents": "Verification documents should be purged according to retention policy."})
    UserSession.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())
    record_operational_event("account_deletion_requested", actor=user, metadata={"request_id": str(item.id)})
    return item, True


def cancel_account_deletion_request(user):
    item = AccountDeletionRequest.objects.filter(user=user, status=AccountDeletionRequest.STATUS_REQUESTED).order_by("-created_at").first()
    if not item:
        return None
    item.status = AccountDeletionRequest.STATUS_CANCELLED; item.cancelled_at = timezone.now(); item.save(update_fields=["status", "cancelled_at", "updated_at"])
    record_operational_event("account_deletion_cancelled", actor=user, metadata={"request_id": str(item.id)})
    return item


def deletion_payload(item):
    return {"id": str(item.id), "status": item.status, "reason": item.reason, "grace_period_ends_at": item.grace_period_ends_at.isoformat(), "cancelled_at": item.cancelled_at.isoformat() if item.cancelled_at else None, "completed_at": item.completed_at.isoformat() if item.completed_at else None, "retention_notes": item.retention_notes, "created_at": item.created_at.isoformat()}


def database_ready():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        return cursor.fetchone()[0] == 1


def readiness_report():
    checks = {"database": False, "redis_configured": bool(getattr(settings, "REDIS_URL", "")), "channel_layer": bool(getattr(settings, "CHANNEL_LAYERS", None)), "email_configured": bool(getattr(settings, "DEFAULT_FROM_EMAIL", "")), "storage_configured": bool(getattr(settings, "MANYUMBU_MEDIA_PROVIDER", "local")), "celery_configured": bool(getattr(settings, "CELERY_BROKER_URL", ""))}
    try:
        checks["database"] = database_ready()
    except Exception:
        checks["database"] = False
    return checks
