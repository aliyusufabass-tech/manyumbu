import json
from datetime import timedelta

from django.core import mail
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from .models import EmailVerificationCode, normalize_phone_number


class PhaseOneAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_payload = {
            "full_name": "Asha Manyumbu",
            "username": "asha",
            "phone_number": "0714123456",
            "email": "asha@example.com",
            "date_of_birth": "2000-05-10",
            "password": "StrongerPass123!",
            "confirm_password": "StrongerPass123!",
            "accepted_terms": True,
            "accepted_privacy": True,
        }

    def post_json(self, url, payload):
        return self.client.post(url, data=json.dumps(payload), content_type="application/json")

    def register_user(self):
        response = self.post_json("/api/v1/auth/register/", self.register_payload)
        self.assertEqual(response.status_code, 201, response.content)
        return get_user_model().objects.get(phone_number="+255714123456")

    def latest_code(self, user):
        email = mail.outbox[-1].body
        for line in email.splitlines():
            line = line.strip()
            if len(line) == 6 and line.isdigit():
                return line
        self.fail("Verification code was not present in test email body.")

    def test_phone_normalization(self):
        self.assertEqual(normalize_phone_number("0714 123 456"), "+255714123456")
        self.assertEqual(normalize_phone_number("+254712345678"), "+254712345678")
        self.assertEqual(normalize_phone_number("255714123456"), "+255714123456")

    def test_registration_creates_inactive_user_and_sends_hidden_code(self):
        user = self.register_user()
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn(self.latest_code(user), self.post_json("/api/v1/auth/register/", self.register_payload).content.decode())

    def test_duplicate_phone_number_is_rejected(self):
        self.register_user()
        duplicate = {**self.register_payload, "email": "other@example.com", "username": "other"}
        response = self.post_json("/api/v1/auth/register/", duplicate)
        self.assertEqual(response.status_code, 409)

    def test_email_verification_activates_user_and_returns_tokens(self):
        user = self.register_user()
        code = self.latest_code(user)
        response = self.post_json("/api/v1/auth/verify-email/", {"phone_number": user.phone_number, "code": code})
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()["data"]
        self.assertIn("access", data["tokens"])
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_email_verified)
        self.assertIsNotNone(user.email_verified_at)

    def test_incorrect_code_increments_attempts(self):
        user = self.register_user()
        response = self.post_json("/api/v1/auth/verify-email/", {"phone_number": user.phone_number, "code": "000000"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(user.email_verification_codes.latest("created_at").failed_attempts, 1)

    def test_expired_code_is_rejected(self):
        user = self.register_user()
        record = user.email_verification_codes.latest("created_at")
        record.expires_at = timezone.now() - timedelta(seconds=1)
        record.save(update_fields=["expires_at"])
        response = self.post_json("/api/v1/auth/verify-email/", {"phone_number": user.phone_number, "code": self.latest_code(user)})
        self.assertEqual(response.status_code, 410)

    def test_unverified_user_cannot_login(self):
        self.register_user()
        response = self.post_json("/api/v1/auth/login/", {"identifier": "asha", "password": "StrongerPass123!"})
        self.assertEqual(response.status_code, 403)

    def test_verified_user_can_login_with_phone_email_or_username(self):
        user = self.register_user()
        code = self.latest_code(user)
        self.post_json("/api/v1/auth/verify-email/", {"phone_number": user.phone_number, "code": code})
        for identifier in ["+255714123456", "asha@example.com", "asha"]:
            response = self.post_json("/api/v1/auth/login/", {"identifier": identifier, "password": "StrongerPass123!"})
            self.assertEqual(response.status_code, 200, response.content)
            self.assertIn("refresh", response.json()["data"]["tokens"])

    def test_forgot_and_reset_password(self):
        user = self.register_user()
        code = self.latest_code(user)
        self.post_json("/api/v1/auth/verify-email/", {"phone_number": user.phone_number, "code": code})
        response = self.post_json("/api/v1/auth/forgot-password/", {"identifier": "asha@example.com"})
        self.assertEqual(response.status_code, 200)
        reset_code = next(line.strip().strip(".") for line in mail.outbox[-1].body.split() if line.strip(".").isdigit() and len(line.strip(".")) == 6)
        response = self.post_json(
            "/api/v1/auth/reset-password/",
            {"identifier": "asha@example.com", "code": reset_code, "password": "NewStrongPass123!", "confirm_password": "NewStrongPass123!"},
        )
        self.assertEqual(response.status_code, 200, response.content)
        response = self.post_json("/api/v1/auth/login/", {"identifier": "asha", "password": "NewStrongPass123!"})
        self.assertEqual(response.status_code, 200, response.content)

    def test_google_start_requires_phone_for_new_google_user(self):
        response = self.post_json(
            "/api/v1/auth/google/start/",
            {"google_sub": "google-123", "email": "google@example.com", "email_verified": True},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["requires_phone_number"])
