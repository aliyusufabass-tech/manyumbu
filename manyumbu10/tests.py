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

from .models import BlockedUser, CloseFriend, Follow, FollowRequest, MutedUser, RestrictedUser, UserPrivacySettings
from .services import ensure_profile_records, issue_tokens


class PhaseTwoProfileRelationshipTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.alice = User.objects.create_user(
            phone_number="+255700000001",
            email="alice@example.com",
            username="alice",
            full_name="Alice Manyumbu",
            date_of_birth="1998-01-01",
            password="StrongerPass123!",
            is_active=True,
            is_email_verified=True,
        )
        self.bob = User.objects.create_user(
            phone_number="+255700000002",
            email="bob@example.com",
            username="bob",
            full_name="Bob River",
            date_of_birth="1999-02-02",
            password="StrongerPass123!",
            is_active=True,
            is_email_verified=True,
        )
        self.caro = User.objects.create_user(
            phone_number="+255700000003",
            email="caro@example.com",
            username="caro",
            full_name="Caro Hill",
            date_of_birth="1997-03-03",
            password="StrongerPass123!",
            is_active=True,
            is_email_verified=True,
        )
        for user in [self.alice, self.bob, self.caro]:
            ensure_profile_records(user)
        self.alice_token = issue_tokens(self.alice)["access"]
        self.bob_token = issue_tokens(self.bob)["access"]
        self.caro_token = issue_tokens(self.caro)["access"]

    def auth(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def post_json_auth(self, url, payload=None, token=None):
        return self.client.post(url, data=json.dumps(payload or {}), content_type="application/json", **self.auth(token or self.alice_token))

    def patch_json_auth(self, url, payload=None, token=None):
        return self.client.patch(url, data=json.dumps(payload or {}), content_type="application/json", **self.auth(token or self.alice_token))

    def test_profile_retrieval_hides_public_phone_number(self):
        response = self.client.get("/api/v1/profiles/bob/", **self.auth(self.alice_token))
        self.assertEqual(response.status_code, 200, response.content)
        profile = response.json()["data"]["profile"]
        self.assertEqual(profile["username"], "bob")
        self.assertNotIn("phone_number", profile)

    def test_own_profile_includes_private_account_fields(self):
        response = self.client.get("/api/v1/profiles/me/", **self.auth(self.alice_token))
        self.assertEqual(response.status_code, 200)
        profile = response.json()["data"]["profile"]
        self.assertEqual(profile["phone_number"], "+255700000001")
        self.assertIn("saved", profile["tabs"])

    def test_profile_edit_and_unique_username_validation(self):
        response = self.patch_json_auth("/api/v1/profiles/me/", {"bio": "Builder", "location": "Dar", "username": "alice_new"})
        self.assertEqual(response.status_code, 200, response.content)
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.username, "alice_new")
        response = self.patch_json_auth("/api/v1/profiles/me/", {"username": "bob"})
        self.assertEqual(response.status_code, 409)

    def test_public_account_follow_and_duplicate_prevention(self):
        response = self.post_json_auth("/api/v1/profiles/bob/follow/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["data"]["state"], "followed")
        response = self.post_json_auth("/api/v1/profiles/bob/follow/")
        self.assertEqual(response.json()["data"]["state"], "already_following")
        self.assertEqual(Follow.objects.filter(follower=self.alice, following=self.bob).count(), 1)

    def test_self_follow_prevention(self):
        response = self.post_json_auth("/api/v1/profiles/alice/follow/")
        self.assertEqual(response.status_code, 400)

    def test_private_account_follow_request_accept_reject_cancel(self):
        self.bob.profile.is_private = True
        self.bob.profile.save()
        response = self.post_json_auth("/api/v1/profiles/bob/follow/")
        self.assertEqual(response.json()["data"]["state"], "requested")
        request_id = response.json()["data"]["request_id"]
        response = self.post_json_auth(f"/api/v1/follow-requests/{request_id}/accept/", token=self.bob_token)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(Follow.objects.filter(follower=self.alice, following=self.bob).exists())

        self.caro.profile.is_private = True
        self.caro.profile.save()
        response = self.post_json_auth("/api/v1/profiles/caro/follow/", token=self.bob_token)
        self.assertEqual(response.status_code, 200)
        request_id = response.json()["data"]["request_id"]
        response = self.post_json_auth(f"/api/v1/follow-requests/{request_id}/cancel/", token=self.bob_token)
        self.assertEqual(response.status_code, 200)

        response = self.post_json_auth("/api/v1/profiles/caro/follow/", token=self.bob_token)
        request_id = response.json()["data"]["request_id"]
        response = self.post_json_auth(f"/api/v1/follow-requests/{request_id}/reject/", token=self.caro_token)
        self.assertEqual(response.status_code, 200)

    def test_remove_follower_and_lists(self):
        Follow.objects.create(follower=self.bob, following=self.alice)
        response = self.client.get("/api/v1/relationships/followers/", **self.auth(self.alice_token))
        self.assertEqual(response.json()["data"]["count"], 1)
        response = self.client.delete("/api/v1/profiles/bob/remove-follower/", **self.auth(self.alice_token))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Follow.objects.filter(follower=self.bob, following=self.alice).exists())

    def test_blocking_removes_follows_requests_and_hides_search(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        FollowRequest.objects.create(requester=self.bob, target=self.alice)
        response = self.post_json_auth("/api/v1/relationships/blocked/bob/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(Follow.objects.filter(follower=self.alice, following=self.bob).exists())
        self.assertFalse(FollowRequest.objects.filter(requester=self.bob, target=self.alice, status=FollowRequest.STATUS_PENDING).exists())
        response = self.client.get("/api/v1/profiles/search/?q=bob", **self.auth(self.alice_token))
        self.assertEqual(response.json()["data"]["count"], 0)
        response = self.client.delete("/api/v1/relationships/blocked/bob/", **self.auth(self.alice_token))
        self.assertEqual(response.status_code, 200)

    def test_restrict_mute_and_close_friends(self):
        self.assertEqual(self.post_json_auth("/api/v1/relationships/restricted/bob/").status_code, 200)
        self.assertTrue(RestrictedUser.objects.filter(owner=self.alice, restricted=self.bob).exists())
        self.assertEqual(self.post_json_auth("/api/v1/relationships/muted/bob/", {"mute_posts": True, "mute_stories": True}).status_code, 200)
        mute = MutedUser.objects.get(owner=self.alice, muted=self.bob)
        self.assertTrue(mute.mute_posts)
        self.assertTrue(mute.mute_stories)
        self.assertEqual(self.post_json_auth("/api/v1/relationships/close-friends/bob/").status_code, 200)
        self.assertTrue(CloseFriend.objects.filter(owner=self.alice, friend=self.bob).exists())

    def test_blocked_user_cannot_be_close_friend(self):
        BlockedUser.objects.create(blocker=self.alice, blocked=self.bob)
        response = self.post_json_auth("/api/v1/relationships/close-friends/bob/")
        self.assertEqual(response.status_code, 403)

    def test_privacy_changes_phone_discoverability_and_private_profile(self):
        response = self.client.get("/api/v1/profiles/search/?q=%2B255700000002", **self.auth(self.alice_token))
        self.assertEqual(response.json()["data"]["count"], 0)
        self.patch_json_auth("/api/v1/profiles/privacy/", {"phone_discoverable": True}, token=self.bob_token)
        response = self.client.get("/api/v1/profiles/search/?q=%2B255700000002", **self.auth(self.alice_token))
        self.assertEqual(response.json()["data"]["count"], 1)
        self.patch_json_auth("/api/v1/profiles/me/", {"is_private": True, "bio": "secret"}, token=self.bob_token)
        response = self.client.get("/api/v1/profiles/bob/", **self.auth(self.alice_token))
        self.assertFalse(response.json()["data"]["profile"]["viewer_can_view_private_content"])
        self.assertEqual(response.json()["data"]["profile"]["bio"], "")

    def test_private_to_public_accepts_valid_pending_requests(self):
        self.bob.profile.is_private = True
        self.bob.profile.save()
        self.post_json_auth("/api/v1/profiles/bob/follow/")
        self.patch_json_auth("/api/v1/profiles/me/", {"is_private": False}, token=self.bob_token)
        self.assertTrue(Follow.objects.filter(follower=self.alice, following=self.bob).exists())

