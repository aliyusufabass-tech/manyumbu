import base64
import hashlib
import hmac
import json
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.template.loader import render_to_string
from django.utils import timezone

from .models import EmailVerificationCode, PasswordResetCode, UserProfile, UserSession, normalize_phone_number

MAX_CODE_ATTEMPTS = 5


def generate_six_digit_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_token(user, token_type: str, lifetime: timedelta, token_id: str | None = None) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = timezone.now()
    payload = {
        "sub": user.phone_number,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
        "jti": token_id or secrets.token_urlsafe(18),
    }
    signing_input = f"{_b64(json.dumps(header, separators=(',', ':')).encode())}.{_b64(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(settings.SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(signature)}"


def decode_token(token: str, expected_type: str | None = None) -> dict:
    try:
        head, body, signature = token.split(".")
        signing_input = f"{head}.{body}"
        expected = _b64(hmac.new(settings.SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid token signature.")
        payload = json.loads(_unb64(body))
    except Exception as exc:
        raise ValueError("Invalid token.") from exc
    if expected_type and payload.get("type") != expected_type:
        raise ValueError("Invalid token type.")
    if timezone.now().timestamp() >= payload.get("exp", 0):
        raise ValueError("Token has expired.")
    return payload


def issue_tokens(user, request=None, device_name="") -> dict:
    refresh_id = secrets.token_urlsafe(24)
    access = create_token(user, "access", settings.MANYUMBU_ACCESS_TOKEN_LIFETIME)
    refresh = create_token(user, "refresh", settings.MANYUMBU_REFRESH_TOKEN_LIFETIME, refresh_id)
    UserSession.objects.create(
        user=user,
        refresh_token_hash=hash_token(refresh_id),
        device_name=device_name[:120],
        ip_address=get_client_ip(request) if request else None,
        user_agent=(request.META.get("HTTP_USER_AGENT", "") if request else ""),
    )
    return {"access": access, "refresh": refresh}


def get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    return (forwarded.split(",")[0] if forwarded else request.META.get("REMOTE_ADDR")) or None


def send_verification_email(user, code: str):
    context = {"full_name": user.full_name, "code": code}
    subject = "Verify your Manyumbu account"
    text_body = render_to_string("emails/verification_code.txt", context)
    html_body = render_to_string("emails/verification_code.html", context)
    send_mail(subject, text_body, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_body, fail_silently=False)


def send_password_reset_email(user, code: str):
    subject = "Reset your Manyumbu password"
    message = f"Welcome to Manyumbu.\n\nYour password reset code is {code}.\n\nThis code expires in 10 minutes."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


@transaction.atomic
def create_email_code(user, request=None, device_name=""):
    latest = user.email_verification_codes.order_by("-created_at").first()
    if latest and latest.created_at > timezone.now() - timedelta(seconds=60):
        seconds = int(60 - (timezone.now() - latest.created_at).total_seconds())
        raise ValueError(f"Please wait {max(seconds, 1)} seconds before requesting another code.")
    user.email_verification_codes.filter(used_at__isnull=True).update(used_at=timezone.now())
    code = generate_six_digit_code()
    EmailVerificationCode.objects.create(
        user=user,
        code_hash=make_password(code),
        expires_at=EmailVerificationCode.expiry_time(),
        created_ip=get_client_ip(request) if request else None,
        created_device=device_name[:120],
    )
    send_verification_email(user, code)


def verify_email_code(user, code: str, request=None):
    record = user.email_verification_codes.filter(used_at__isnull=True).order_by("-created_at").first()
    if not record:
        raise ValueError("No active verification code was found.")
    if record.failed_attempts >= MAX_CODE_ATTEMPTS:
        raise PermissionError("Too many incorrect attempts. Request a new code.")
    if record.is_expired:
        raise TimeoutError("Verification code has expired.")
    if not check_password(code, record.code_hash):
        EmailVerificationCode.objects.filter(pk=record.pk).update(failed_attempts=F("failed_attempts") + 1, updated_at=timezone.now())
        raise ValueError("Invalid verification code.")
    now = timezone.now()
    record.used_at = now
    record.save(update_fields=["used_at", "updated_at"])
    user.is_email_verified = True
    user.is_active = True
    user.email_verified_at = now
    user.save(update_fields=["is_email_verified", "is_active", "email_verified_at", "updated_at"])
    UserProfile.objects.get_or_create(user=user)
    return issue_tokens(user, request=request)


def authenticate_identifier(identifier: str, password: str):
    User = get_user_model()
    lookup = identifier.strip()
    user = None
    if "@" in lookup:
        user = User.objects.filter(email__iexact=lookup).first()
    else:
        try:
            phone = normalize_phone_number(lookup)
            user = User.objects.filter(phone_number=phone).first()
        except Exception:
            user = User.objects.filter(username__iexact=lookup).first()
    if not user or not user.check_password(password):
        return None
    return user


def create_password_reset_code(user):
    user.password_reset_codes.filter(used_at__isnull=True).update(used_at=timezone.now())
    code = generate_six_digit_code()
    PasswordResetCode.objects.create(user=user, code_hash=make_password(code), expires_at=timezone.now() + timedelta(minutes=10))
    send_password_reset_email(user, code)


def complete_password_reset(user, code: str, new_password: str):
    record = user.password_reset_codes.filter(used_at__isnull=True).order_by("-created_at").first()
    if not record:
        raise ValueError("No active reset code was found.")
    if record.failed_attempts >= MAX_CODE_ATTEMPTS:
        raise PermissionError("Too many incorrect attempts. Request a new code.")
    if timezone.now() >= record.expires_at:
        raise TimeoutError("Password reset code has expired.")
    if not check_password(code, record.code_hash):
        PasswordResetCode.objects.filter(pk=record.pk).update(failed_attempts=F("failed_attempts") + 1, updated_at=timezone.now())
        raise ValueError("Invalid reset code.")
    record.used_at = timezone.now()
    record.save(update_fields=["used_at", "updated_at"])
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])


