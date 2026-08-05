import shutil
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import AccountDeletionRequest, DataExportRequest, GroupInvitation, Notification, OperationalEvent, Story, UserFeatureRestriction
from .phase8_services import record_operational_event


@shared_task
def send_notification_email(subject, message, recipient_list):
    if not recipient_list:
        return {"sent": 0, "reason": "no_recipients"}
    sent = send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list, fail_silently=False)
    return {"sent": sent}


@shared_task
def fanout_pending_notifications(limit=200):
    pending = Notification.objects.filter(is_read=False).order_by("created_at")[:limit]
    return {"queued_notifications": len(list(pending)), "provider": getattr(settings, "MANYUMBU_PUSH_PROVIDER", "none")}


@shared_task
def expire_old_stories():
    expired = Story.objects.filter(expires_at__lte=timezone.now(), status=Story.STATUS_PUBLISHED).update(status=Story.STATUS_EXPIRED)
    return {"expired_stories": expired}


@shared_task
def process_media_asset(asset_path):
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        record_operational_event("media_processing_unavailable", "warning", metadata={"asset_path": asset_path})
        return {"status": "skipped", "reason": "ffmpeg_unavailable"}
    return {"status": "ready", "ffmpeg": ffmpeg_path, "asset_path": asset_path}


@shared_task
def expire_data_exports():
    expired = DataExportRequest.objects.filter(status=DataExportRequest.STATUS_READY, expires_at__lte=timezone.now()).update(status=DataExportRequest.STATUS_EXPIRED)
    return {"expired_exports": expired}


@shared_task
def process_account_deletions(limit=50):
    due = AccountDeletionRequest.objects.filter(status=AccountDeletionRequest.STATUS_REQUESTED, grace_period_ends_at__lte=timezone.now()).order_by("created_at")[:limit]
    count = 0
    for item in due:
        item.status = AccountDeletionRequest.STATUS_PROCESSING
        item.save(update_fields=["status", "updated_at"])
        count += 1
        record_operational_event("account_deletion_ready_for_operator", "warning", actor=item.user, metadata={"request_id": str(item.id)})
    return {"marked_for_operator_review": count}


@shared_task
def cleanup_expired_safety_records():
    now = timezone.now()
    expired_invites = GroupInvitation.objects.filter(expires_at__lt=now, revoked_at__isnull=True).count()
    expired_restrictions = UserFeatureRestriction.objects.filter(expires_at__lt=now, status=UserFeatureRestriction.STATUS_ACTIVE).update(status=UserFeatureRestriction.STATUS_EXPIRED)
    return {"expired_group_invitations": expired_invites, "expired_feature_restrictions": expired_restrictions}


@shared_task
def aggregate_operational_metrics(window_minutes=60):
    since = timezone.now() - timedelta(minutes=window_minutes)
    events = OperationalEvent.objects.filter(created_at__gte=since).count()
    return {"window_minutes": window_minutes, "operational_events": events}


@shared_task
def run_backup_checkpoint():
    return {"status": "operator_action_required", "script": "scripts/backup_database.sh", "storage": "configure BACKUP_DIR or cloud upload outside the worker"}
