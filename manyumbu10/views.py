import json
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import GoogleAccount, normalize_phone_number
from .services import (
    authenticate_identifier,
    complete_password_reset,
    create_email_code,
    create_password_reset_code,
    decode_token,
    hash_token,
    issue_tokens,
    verify_email_code,
)


def response(success, message, data=None, status=200):
    return JsonResponse({"success": success, "message": message, "data": data or {}}, status=status)


def body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        raise ValueError("Request body must be valid JSON.")


def required(payload, fields):
    missing = [field for field in fields if payload.get(field) in (None, "")]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}.")


def check_age(value):
    try:
        born = date.fromisoformat(value)
    except Exception as exc:
        raise ValueError("date_of_birth must be YYYY-MM-DD.") from exc
    today = date.today()
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    if age < 13:
        raise ValueError("Users must be at least 13 years old.")
    return born


def public_user(user):
    return {
        "phone_number": user.phone_number,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "is_email_verified": user.is_email_verified,
        "is_active": user.is_active,
    }


@method_decorator(csrf_exempt, name="dispatch")
class RegisterView(View):
    def post(self, request):
        try:
            payload = body(request)
            required(payload, ["full_name", "username", "phone_number", "email", "date_of_birth", "password", "confirm_password"])
            if not payload.get("accepted_terms") or not payload.get("accepted_privacy"):
                return response(False, "Terms and Privacy Policy acceptance is required.", status=400)
            if payload["password"] != payload["confirm_password"]:
                return response(False, "Passwords do not match.", status=400)
            validate_password(payload["password"])
            normalized_phone = normalize_phone_number(payload["phone_number"])
            dob = check_age(payload["date_of_birth"])
            User = get_user_model()
            if User.objects.filter(phone_number=normalized_phone).exists() or User.objects.filter(email__iexact=payload["email"]).exists() or User.objects.filter(username__iexact=payload["username"].strip().lower()).exists():
                return response(False, "Phone number, email, or username already exists.", status=409)
            with transaction.atomic():
                user = User.objects.create_user(
                    phone_number=normalized_phone,
                    email=payload["email"],
                    username=payload["username"],
                    full_name=payload["full_name"],
                    date_of_birth=dob,
                    password=payload["password"],
                    is_active=False,
                    is_email_verified=False,
                )
                create_email_code(user, request=request, device_name=payload.get("device_name", ""))
            return response(True, "Account created. Check your email for the verification code.", {"user": public_user(user)}, status=201)
        except IntegrityError:
            return response(False, "Phone number, email, or username already exists.", status=409)
        except (ValueError, ValidationError) as exc:
            detail = exc.messages if hasattr(exc, "messages") else str(exc)
            return response(False, detail, status=400)


@method_decorator(csrf_exempt, name="dispatch")
class VerifyEmailView(View):
    def post(self, request):
        try:
            payload = body(request)
            required(payload, ["phone_number", "code"])
            if len(str(payload["code"])) != 6 or not str(payload["code"]).isdigit():
                return response(False, "Verification code must contain exactly six digits.", status=400)
            User = get_user_model()
            user = User.objects.get(phone_number=normalize_phone_number(payload["phone_number"]))
            tokens = verify_email_code(user, str(payload["code"]), request=request)
            return response(True, "Account verified successfully.", {"user": public_user(user), "tokens": tokens})
        except User.DoesNotExist:
            return response(False, "User was not found.", status=404)
        except TimeoutError as exc:
            return response(False, str(exc), status=410)
        except PermissionError as exc:
            return response(False, str(exc), status=429)
        except (ValueError, ValidationError) as exc:
            detail = exc.messages if hasattr(exc, "messages") else str(exc)
            return response(False, detail, status=400)


@method_decorator(csrf_exempt, name="dispatch")
class ResendVerificationView(View):
    def post(self, request):
        try:
            payload = body(request)
            required(payload, ["phone_number"])
            User = get_user_model()
            user = User.objects.get(phone_number=normalize_phone_number(payload["phone_number"]))
            if user.is_email_verified:
                return response(False, "Email is already verified.", status=400)
            create_email_code(user, request=request, device_name=payload.get("device_name", ""))
            return response(True, "A new verification code has been sent.")
        except User.DoesNotExist:
            return response(False, "User was not found.", status=404)
        except ValueError as exc:
            return response(False, str(exc), status=429 if "wait" in str(exc).lower() else 400)


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(View):
    def post(self, request):
        try:
            payload = body(request)
            required(payload, ["identifier", "password"])
            user = authenticate_identifier(payload["identifier"], payload["password"])
            if not user:
                return response(False, "Invalid credentials.", status=401)
            if not user.is_active or not user.is_email_verified:
                return response(False, "Please verify your email before signing in.", {"verification_required": True}, status=403)
            tokens = issue_tokens(user, request=request, device_name=payload.get("device_name", ""))
            return response(True, "Signed in successfully.", {"user": public_user(user), "tokens": tokens})
        except ValueError as exc:
            return response(False, str(exc), status=400)


@method_decorator(csrf_exempt, name="dispatch")
class TokenRefreshView(View):
    def post(self, request):
        try:
            payload = body(request)
            required(payload, ["refresh"])
            decoded = decode_token(payload["refresh"], expected_type="refresh")
            User = get_user_model()
            user = User.objects.get(phone_number=decoded["sub"], is_active=True, is_email_verified=True)
            session = user.sessions.filter(refresh_token_hash=hash_token(decoded["jti"]), revoked_at__isnull=True).first()
            if not session:
                return response(False, "Refresh token is no longer valid.", status=401)
            tokens = issue_tokens(user, request=request)
            from django.utils import timezone
            session.revoked_at = timezone.now()
            session.save(update_fields=["revoked_at", "updated_at"])
            return response(True, "Token refreshed successfully.", {"tokens": tokens})
        except Exception as exc:
            return response(False, str(exc), status=401)


@method_decorator(csrf_exempt, name="dispatch")
class ForgotPasswordView(View):
    def post(self, request):
        try:
            payload = body(request)
            required(payload, ["identifier"])
            user = authenticate_identifier(payload["identifier"], payload.get("password", "__never__"))
            if not user:
                User = get_user_model()
                lookup = payload["identifier"].strip()
                user = User.objects.filter(email__iexact=lookup).first() or User.objects.filter(username__iexact=lookup).first()
                if not user:
                    try:
                        user = User.objects.filter(phone_number=normalize_phone_number(lookup)).first()
                    except Exception:
                        user = None
            if user:
                create_password_reset_code(user)
            return response(True, "If the account exists, a reset code has been sent.")
        except ValueError as exc:
            return response(False, str(exc), status=400)


@method_decorator(csrf_exempt, name="dispatch")
class ResetPasswordView(View):
    def post(self, request):
        try:
            payload = body(request)
            required(payload, ["identifier", "code", "password", "confirm_password"])
            if payload["password"] != payload["confirm_password"]:
                return response(False, "Passwords do not match.", status=400)
            validate_password(payload["password"])
            User = get_user_model()
            lookup = payload["identifier"].strip()
            user = User.objects.filter(email__iexact=lookup).first() or User.objects.filter(username__iexact=lookup).first()
            if not user:
                user = User.objects.get(phone_number=normalize_phone_number(lookup))
            complete_password_reset(user, str(payload["code"]), payload["password"])
            return response(True, "Password reset successfully.")
        except User.DoesNotExist:
            return response(False, "User was not found.", status=404)
        except TimeoutError as exc:
            return response(False, str(exc), status=410)
        except PermissionError as exc:
            return response(False, str(exc), status=429)
        except (ValueError, ValidationError) as exc:
            detail = exc.messages if hasattr(exc, "messages") else str(exc)
            return response(False, detail, status=400)


@method_decorator(csrf_exempt, name="dispatch")
class GoogleAuthStartView(View):
    def post(self, request):
        try:
            payload = body(request)
            required(payload, ["google_sub", "email", "email_verified"])
            if not payload["email_verified"]:
                return response(False, "Google email must be verified.", status=400)
            account, _ = GoogleAccount.objects.get_or_create(
                google_sub=payload["google_sub"],
                defaults={"email": payload["email"], "is_verified_email": True, "pending_payload": payload},
            )
            if account.user and account.user.is_active:
                tokens = issue_tokens(account.user, request=request)
                return response(True, "Signed in with Google successfully.", {"user": public_user(account.user), "tokens": tokens})
            account.pending_payload = payload
            account.email = payload["email"]
            account.is_verified_email = True
            account.save(update_fields=["pending_payload", "email", "is_verified_email", "updated_at"])
            return response(True, "Phone number and profile details are required to finish Google sign-in.", {"requires_phone_number": True})
        except ValueError as exc:
            return response(False, str(exc), status=400)

