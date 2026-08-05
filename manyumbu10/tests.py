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


from django.core.files.uploadedfile import SimpleUploadedFile
from .models import AdminAuditLog, Comment, HiddenPost, Hashtag, Notification, Post, PostLike, PostReport, SavedPost


class PhaseThreePostFeedTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.alice = User.objects.create_user("+255711000001", "pa@example.com", "postalice", "Post Alice", "StrongerPass123!", date_of_birth="1995-01-01", is_active=True, is_email_verified=True)
        self.bob = User.objects.create_user("+255711000002", "pb@example.com", "postbob", "Post Bob", "StrongerPass123!", date_of_birth="1995-01-01", is_active=True, is_email_verified=True)
        self.caro = User.objects.create_user("+255711000003", "pc@example.com", "postcaro", "Post Caro", "StrongerPass123!", date_of_birth="1995-01-01", is_active=True, is_email_verified=True)
        for user in [self.alice, self.bob, self.caro]:
            ensure_profile_records(user)
        self.alice_token = issue_tokens(self.alice)["access"]
        self.bob_token = issue_tokens(self.bob)["access"]
        self.caro_token = issue_tokens(self.caro)["access"]

    def auth(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def post_json(self, url, payload=None, token=None):
        return self.client.post(url, data=json.dumps(payload or {}), content_type="application/json", **self.auth(token or self.alice_token))

    def patch_json(self, url, payload=None, token=None):
        return self.client.patch(url, data=json.dumps(payload or {}), content_type="application/json", **self.auth(token or self.alice_token))

    def create_text_post(self, author_token=None, **extra):
        payload = {"caption": "Hello #Manyumbu @postbob", "audience": "public", **extra}
        response = self.post_json("/api/v1/posts/", payload, token=author_token or self.alice_token)
        self.assertEqual(response.status_code, 201, response.content)
        return Post.objects.get(id=response.json()["data"]["post"]["id"])

    def test_text_post_creation_hashtags_and_mentions(self):
        post = self.create_text_post()
        self.assertEqual(post.post_type, Post.TYPE_TEXT)
        self.assertTrue(Hashtag.objects.filter(name="manyumbu").exists())
        self.assertTrue(post.mentions.filter(user=self.bob).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.bob, notification_type=Notification.TYPE_POST_MENTION).exists())

    def test_empty_post_rejected_and_caption_limit(self):
        response = self.post_json("/api/v1/posts/", {"caption": ""})
        self.assertEqual(response.status_code, 400)
        response = self.post_json("/api/v1/posts/", {"caption": "x" * 2201})
        self.assertEqual(response.status_code, 400)

    def test_image_post_creation_and_ordering(self):
        first = SimpleUploadedFile("a.jpg", b"abc", content_type="image/jpeg")
        second = SimpleUploadedFile("b.png", b"def", content_type="image/png")
        response = self.client.post("/api/v1/posts/", {"caption": "photos", "media": [first, second]}, **self.auth(self.alice_token))
        self.assertEqual(response.status_code, 201, response.content)
        post = Post.objects.get(id=response.json()["data"]["post"]["id"])
        self.assertEqual(post.post_type, Post.TYPE_IMAGE)
        self.assertEqual(list(post.media.order_by("display_order").values_list("display_order", flat=True)), [0, 1])

    def test_video_validation_rejects_mixed_media(self):
        image = SimpleUploadedFile("a.jpg", b"abc", content_type="image/jpeg")
        video = SimpleUploadedFile("v.mp4", b"video", content_type="video/mp4")
        response = self.client.post("/api/v1/posts/", {"caption": "mixed", "media": [image, video]}, **self.auth(self.alice_token))
        self.assertEqual(response.status_code, 400)

    def test_public_followers_close_friends_selected_only_me_visibility(self):
        public = self.create_text_post(caption="public")
        followers = self.create_text_post(audience=Post.AUDIENCE_FOLLOWERS, caption="followers")
        close = self.create_text_post(audience=Post.AUDIENCE_CLOSE_FRIENDS, caption="close")
        selected = self.create_text_post(audience=Post.AUDIENCE_SELECTED, caption="selected", selected_users=["postbob"])
        only_me = self.create_text_post(audience=Post.AUDIENCE_ONLY_ME, caption="only")
        self.assertEqual(self.client.get(f"/api/v1/posts/{public.id}/", **self.auth(self.bob_token)).status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/posts/{followers.id}/", **self.auth(self.bob_token)).status_code, 403)
        Follow.objects.create(follower=self.bob, following=self.alice)
        self.assertEqual(self.client.get(f"/api/v1/posts/{followers.id}/", **self.auth(self.bob_token)).status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/posts/{close.id}/", **self.auth(self.bob_token)).status_code, 403)
        CloseFriend.objects.create(owner=self.alice, friend=self.bob)
        self.assertEqual(self.client.get(f"/api/v1/posts/{close.id}/", **self.auth(self.bob_token)).status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/posts/{selected.id}/", **self.auth(self.bob_token)).status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/posts/{only_me.id}/", **self.auth(self.bob_token)).status_code, 403)

    def test_private_account_and_blocked_user_visibility(self):
        self.alice.profile.is_private = True
        self.alice.profile.save()
        post = self.create_text_post(caption="private")
        self.assertEqual(self.client.get(f"/api/v1/posts/{post.id}/", **self.auth(self.bob_token)).status_code, 403)
        Follow.objects.create(follower=self.bob, following=self.alice)
        self.assertEqual(self.client.get(f"/api/v1/posts/{post.id}/", **self.auth(self.bob_token)).status_code, 200)
        BlockedUser.objects.create(blocker=self.alice, blocked=self.bob)
        self.assertEqual(self.client.get(f"/api/v1/posts/{post.id}/", **self.auth(self.bob_token)).status_code, 403)

    def test_muted_and_hidden_posts_are_filtered_from_feed(self):
        post = self.create_text_post(caption="feed")
        response = self.client.get("/api/v1/feed/", **self.auth(self.bob_token))
        self.assertEqual(len(response.json()["data"]["results"]), 1)
        MutedUser.objects.create(owner=self.bob, muted=self.alice, mute_posts=True)
        response = self.client.get("/api/v1/feed/", **self.auth(self.bob_token))
        self.assertEqual(len(response.json()["data"]["results"]), 0)
        MutedUser.objects.all().delete()
        self.post_json(f"/api/v1/posts/{post.id}/hide/", token=self.bob_token)
        response = self.client.get("/api/v1/feed/", **self.auth(self.bob_token))
        self.assertEqual(len(response.json()["data"]["results"]), 0)

    def test_like_unlike_and_duplicate_like_prevention(self):
        post = self.create_text_post()
        self.assertEqual(self.post_json(f"/api/v1/posts/{post.id}/like/", token=self.bob_token).status_code, 200)
        self.assertEqual(self.post_json(f"/api/v1/posts/{post.id}/like/", token=self.bob_token).status_code, 200)
        self.assertEqual(PostLike.objects.filter(post=post, user=self.bob).count(), 1)
        self.assertTrue(Notification.objects.filter(recipient=self.alice, notification_type=Notification.TYPE_POST_LIKED).exists())
        response = self.client.delete(f"/api/v1/posts/{post.id}/like/", **self.auth(self.bob_token))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(PostLike.objects.filter(post=post, user=self.bob).exists())

    def test_comments_replies_disabled_edit_delete_and_likes(self):
        post = self.create_text_post()
        response = self.post_json(f"/api/v1/posts/{post.id}/comments/", {"text": "Nice"}, token=self.bob_token)
        self.assertEqual(response.status_code, 201, response.content)
        comment_id = response.json()["data"]["comment"]["id"]
        reply = self.post_json(f"/api/v1/posts/{post.id}/comments/", {"text": "Thanks", "parent_id": comment_id})
        self.assertEqual(reply.status_code, 201)
        self.assertEqual(self.post_json(f"/api/v1/comments/{comment_id}/like/").status_code, 200)
        self.assertEqual(self.patch_json(f"/api/v1/comments/{comment_id}/", {"text": "Edited"}).status_code, 403)
        self.assertEqual(self.patch_json(f"/api/v1/comments/{comment_id}/", {"text": "Edited"}, token=self.bob_token).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/v1/comments/{comment_id}/", **self.auth(self.bob_token)).status_code, 200)
        post.comments_enabled = False
        post.save()
        response = self.post_json(f"/api/v1/posts/{post.id}/comments/", {"text": "Nope"}, token=self.bob_token)
        self.assertEqual(response.status_code, 403)

    def test_saved_posts_private_to_saver(self):
        post = self.create_text_post()
        self.assertEqual(self.post_json(f"/api/v1/posts/{post.id}/save/", token=self.bob_token).status_code, 200)
        self.assertTrue(SavedPost.objects.filter(post=post, user=self.bob).exists())
        response = self.client.get("/api/v1/me/saved-posts/", **self.auth(self.bob_token))
        self.assertEqual(response.json()["data"]["count"], 1)
        response = self.client.delete(f"/api/v1/posts/{post.id}/save/", **self.auth(self.bob_token))
        self.assertEqual(response.status_code, 200)

    def test_archive_restore_and_soft_delete(self):
        post = self.create_text_post()
        self.assertEqual(self.post_json(f"/api/v1/posts/{post.id}/archive/").status_code, 200)
        post.refresh_from_db()
        self.assertEqual(post.status, Post.STATUS_ARCHIVED)
        self.assertEqual(self.client.get("/api/v1/me/archived-posts/", **self.auth(self.alice_token)).json()["data"]["count"], 1)
        self.assertEqual(self.post_json(f"/api/v1/posts/{post.id}/restore/").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/v1/posts/{post.id}/", **self.auth(self.alice_token)).status_code, 200)
        post.refresh_from_db()
        self.assertEqual(post.status, Post.STATUS_DELETED)

    def test_owner_only_edit_and_delete(self):
        post = self.create_text_post()
        self.assertEqual(self.patch_json(f"/api/v1/posts/{post.id}/", {"caption": "bad"}, token=self.bob_token).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/v1/posts/{post.id}/", **self.auth(self.bob_token)).status_code, 403)
        response = self.patch_json(f"/api/v1/posts/{post.id}/", {"caption": "new #Zanzibar"})
        self.assertEqual(response.status_code, 200)
        post.refresh_from_db()
        self.assertTrue(post.is_edited)
        self.assertTrue(Hashtag.objects.filter(name="zanzibar").exists())

    def test_hashtag_posts_and_feed_cursor_no_duplicates(self):
        first = self.create_text_post(caption="one #tag")
        second = self.create_text_post(caption="two #tag")
        response = self.client.get("/api/v1/hashtags/tag/posts/", **self.auth(self.bob_token))
        self.assertEqual(response.json()["data"]["count"], 2)
        response = self.client.get("/api/v1/feed/?limit=1", **self.auth(self.bob_token))
        first_page = response.json()["data"]
        response = self.client.get(f"/api/v1/feed/?limit=1&cursor={first_page['next_cursor']}", **self.auth(self.bob_token))
        second_page = response.json()["data"]
        ids = [item["id"] for item in first_page["results"] + second_page["results"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_post_report_creation_and_blocked_tag_validation(self):
        post = self.create_text_post()
        response = self.post_json(f"/api/v1/posts/{post.id}/report/", {"reason": "spam", "details": "bad"}, token=self.bob_token)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(PostReport.objects.filter(post=post, reporter=self.bob, reason="spam").exists())
        BlockedUser.objects.create(blocker=self.alice, blocked=self.caro)
        response = self.post_json("/api/v1/posts/", {"caption": "tag", "tagged_users": ["postcaro"]})
        self.assertEqual(response.status_code, 403)

class PhaseThreeAdminPostManagementTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("+255722000001", "adminp@example.com", "postadmin", "Post Admin", "StrongerPass123!", date_of_birth="1990-01-01", is_active=True, is_email_verified=True, is_staff=True)
        self.user = User.objects.create_user("+255722000002", "poster@example.com", "poster", "Poster", "StrongerPass123!", date_of_birth="1990-01-01", is_active=True, is_email_verified=True)
        ensure_profile_records(self.admin)
        ensure_profile_records(self.user)
        self.admin_token = issue_tokens(self.admin)["access"]
        self.user_token = issue_tokens(self.user)["access"]
        self.client = Client()
        self.post = Post.objects.create(author=self.user, caption="moderate me", published_at=timezone.now())

    def auth(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_admin_can_list_remove_restore_posts_with_audit_log(self):
        response = self.client.get("/api/v1/admin/posts/?q=moderate", **self.auth(self.admin_token))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["data"]["count"], 1)
        response = self.client.post(f"/api/v1/admin/posts/{self.post.id}/remove/", data=json.dumps({"reason": "policy"}), content_type="application/json", **self.auth(self.admin_token))
        self.assertEqual(response.status_code, 200, response.content)
        self.post.refresh_from_db()
        self.assertEqual(self.post.status, Post.STATUS_REMOVED)
        self.assertTrue(AdminAuditLog.objects.filter(admin_user=self.admin, action="post_remove", target=str(self.post.id)).exists())
        response = self.client.post(f"/api/v1/admin/posts/{self.post.id}/restore/", data=json.dumps({"reason": "appeal"}), content_type="application/json", **self.auth(self.admin_token))
        self.assertEqual(response.status_code, 200)
        self.post.refresh_from_db()
        self.assertEqual(self.post.status, Post.STATUS_PUBLISHED)

    def test_non_staff_cannot_use_admin_post_management(self):
        response = self.client.get("/api/v1/admin/posts/", **self.auth(self.user_token))
        self.assertEqual(response.status_code, 403)


from .models import Reel, ReelLike, ReelReport, ReelView, SavedReel, Story, StoryHighlight, StoryPollVote, StoryReaction, StoryReport, StoryView


class PhaseFourStoryReelTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.alice = User.objects.create_user("+255733000001", "sa@example.com", "storyalice", "Story Alice", "StrongerPass123!", date_of_birth="1995-01-01", is_active=True, is_email_verified=True)
        self.bob = User.objects.create_user("+255733000002", "sb@example.com", "storybob", "Story Bob", "StrongerPass123!", date_of_birth="1995-01-01", is_active=True, is_email_verified=True)
        self.caro = User.objects.create_user("+255733000003", "sc@example.com", "storycaro", "Story Caro", "StrongerPass123!", date_of_birth="1995-01-01", is_active=True, is_email_verified=True)
        self.admin = User.objects.create_user("+255733000004", "sd@example.com", "storyadmin", "Story Admin", "StrongerPass123!", date_of_birth="1990-01-01", is_active=True, is_email_verified=True, is_staff=True)
        for user in [self.alice, self.bob, self.caro, self.admin]:
            ensure_profile_records(user)
        self.alice_token = issue_tokens(self.alice)["access"]
        self.bob_token = issue_tokens(self.bob)["access"]
        self.caro_token = issue_tokens(self.caro)["access"]
        self.admin_token = issue_tokens(self.admin)["access"]

    def auth(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def post_json(self, url, payload=None, token=None):
        return self.client.post(url, data=json.dumps(payload or {}), content_type="application/json", **self.auth(token or self.alice_token))

    def create_story(self, **extra):
        payload = {"caption": "Story #Daily @storybob", "audience": "everyone", **extra}
        response = self.post_json("/api/v1/stories/", payload)
        self.assertEqual(response.status_code, 201, response.content)
        return Story.objects.get(id=response.json()["data"]["story"]["id"])

    def create_reel(self, token=None, **extra):
        video = SimpleUploadedFile("r.mp4", b"video", content_type="video/mp4")
        data = {"caption": "Reel #Dance @storybob", "audience": "public", "duration": "12", **extra, "video": video}
        response = self.client.post("/api/v1/reels/", data, **self.auth(token or self.alice_token))
        self.assertEqual(response.status_code, 201, response.content)
        return Reel.objects.get(id=response.json()["data"]["reel"]["id"])

    def test_text_story_creation_expiration_and_tray_exclusion(self):
        story = self.create_story(background_style="mint")
        self.assertEqual(story.story_type, Story.TYPE_TEXT)
        self.assertIsNotNone(story.expires_at)
        response = self.client.get("/api/v1/stories/tray/", **self.auth(self.bob_token))
        self.assertEqual(response.json()["data"]["count"], 1)
        story.expires_at = timezone.now() - timedelta(seconds=1)
        story.save(update_fields=["expires_at"])
        response = self.client.get("/api/v1/stories/tray/", **self.auth(self.bob_token))
        self.assertEqual(response.json()["data"]["count"], 0)
        story.refresh_from_db()
        self.assertEqual(story.status, Story.STATUS_EXPIRED)

    def test_image_story_video_validation_and_visibility_rules(self):
        image = SimpleUploadedFile("s.jpg", b"image", content_type="image/jpeg")
        response = self.client.post("/api/v1/stories/", {"caption": "image", "media": image}, **self.auth(self.alice_token))
        self.assertEqual(response.status_code, 201, response.content)
        bad = SimpleUploadedFile("s.txt", b"bad", content_type="text/plain")
        response = self.client.post("/api/v1/stories/", {"caption": "bad", "media": bad}, **self.auth(self.alice_token))
        self.assertEqual(response.status_code, 400)
        private = self.create_story(audience=Story.AUDIENCE_FOLLOWERS)
        self.assertEqual(self.client.get(f"/api/v1/stories/{private.id}/", **self.auth(self.bob_token)).status_code, 403)
        Follow.objects.create(follower=self.bob, following=self.alice)
        self.assertEqual(self.client.get(f"/api/v1/stories/{private.id}/", **self.auth(self.bob_token)).status_code, 200)
        close = self.create_story(audience=Story.AUDIENCE_CLOSE_FRIENDS)
        self.assertEqual(self.client.get(f"/api/v1/stories/{close.id}/", **self.auth(self.caro_token)).status_code, 403)
        CloseFriend.objects.create(owner=self.alice, friend=self.caro)
        self.assertEqual(self.client.get(f"/api/v1/stories/{close.id}/", **self.auth(self.caro_token)).status_code, 200)

    def test_selected_hidden_private_blocked_and_muted_story_rules(self):
        selected = self.create_story(audience=Story.AUDIENCE_SELECTED, selected_users=["storybob"])
        self.assertEqual(self.client.get(f"/api/v1/stories/{selected.id}/", **self.auth(self.bob_token)).status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/stories/{selected.id}/", **self.auth(self.caro_token)).status_code, 403)
        hidden = self.create_story(audience=Story.AUDIENCE_HIDE_SELECTED, hidden_users=["storybob"])
        self.assertEqual(self.client.get(f"/api/v1/stories/{hidden.id}/", **self.auth(self.bob_token)).status_code, 403)
        MutedUser.objects.create(owner=self.bob, muted=self.alice, mute_stories=True)
        response = self.client.get("/api/v1/stories/tray/", **self.auth(self.bob_token))
        self.assertEqual(response.json()["data"]["count"], 0)
        BlockedUser.objects.create(blocker=self.alice, blocked=self.caro)
        self.assertEqual(self.client.get(f"/api/v1/stories/{hidden.id}/", **self.auth(self.caro_token)).status_code, 403)

    def test_story_views_viewer_permissions_reactions_replies_reports(self):
        story = self.create_story()
        self.assertEqual(self.post_json(f"/api/v1/stories/{story.id}/view/", token=self.bob_token).status_code, 200)
        self.assertEqual(self.post_json(f"/api/v1/stories/{story.id}/view/", token=self.bob_token).status_code, 200)
        self.assertEqual(StoryView.objects.filter(story=story, viewer=self.bob).count(), 1)
        self.assertEqual(self.client.get(f"/api/v1/stories/{story.id}/viewers/", **self.auth(self.caro_token)).status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/stories/{story.id}/viewers/", **self.auth(self.alice_token)).status_code, 200)
        self.assertEqual(self.post_json(f"/api/v1/stories/{story.id}/react/", {"reaction": "fire"}, token=self.bob_token).status_code, 200)
        self.assertEqual(self.post_json(f"/api/v1/stories/{story.id}/react/", {"reaction": "laugh"}, token=self.bob_token).status_code, 200)
        self.assertEqual(StoryReaction.objects.get(story=story, user=self.bob).reaction, "laugh")
        self.assertEqual(self.post_json(f"/api/v1/stories/{story.id}/reply/", {"text": "Nice"}, token=self.bob_token).status_code, 201)
        story.replies_enabled = False
        story.save(update_fields=["replies_enabled"])
        self.assertEqual(self.post_json(f"/api/v1/stories/{story.id}/reply/", {"text": "No"}, token=self.bob_token).status_code, 403)
        self.assertEqual(self.post_json(f"/api/v1/stories/{story.id}/report/", {"reason": "spam"}, token=self.bob_token).status_code, 200)
        self.assertTrue(StoryReport.objects.filter(story=story, reporter=self.bob).exists())

    def test_story_poll_voting_and_highlights(self):
        story = self.create_story(poll={"question": "Go?", "options": ["Yes", "No"]})
        option = story.poll.options.first()
        self.assertEqual(self.post_json(f"/api/v1/stories/{story.id}/poll-vote/", {"option_id": option.id}, token=self.bob_token).status_code, 200)
        self.assertEqual(self.post_json(f"/api/v1/stories/{story.id}/poll-vote/", {"option_id": option.id}, token=self.bob_token).status_code, 200)
        self.assertEqual(StoryPollVote.objects.filter(poll=story.poll, voter=self.bob).count(), 1)
        story.expires_at = timezone.now() - timedelta(hours=1)
        story.status = Story.STATUS_EXPIRED
        story.save()
        response = self.post_json("/api/v1/highlights/", {"title": "Best"})
        self.assertEqual(response.status_code, 201)
        highlight_id = response.json()["data"]["highlight_id"]
        self.assertEqual(self.post_json(f"/api/v1/highlights/{highlight_id}/stories/", {"story_id": str(story.id)}).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/users/storyalice/highlights/", **self.auth(self.bob_token)).status_code, 200)

    def test_reel_creation_validation_feed_visibility_and_cursor(self):
        first = self.create_reel(caption="one #reel")
        second = self.create_reel(caption="two #reel")
        bad = SimpleUploadedFile("bad.txt", b"bad", content_type="text/plain")
        response = self.client.post("/api/v1/reels/", {"caption": "bad", "video": bad}, **self.auth(self.alice_token))
        self.assertEqual(response.status_code, 400)
        response = self.client.get("/api/v1/reels/feed/?limit=1", **self.auth(self.bob_token))
        self.assertEqual(len(response.json()["data"]["results"]), 1)
        cursor = response.json()["data"]["next_cursor"]
        response = self.client.get(f"/api/v1/reels/feed/?limit=1&cursor={cursor}", **self.auth(self.bob_token))
        ids = [item["id"] for item in response.json()["data"]["results"]]
        self.assertEqual(len(ids), len(set(ids)))
        private = self.create_reel(audience=Post.AUDIENCE_FOLLOWERS)
        self.assertEqual(self.client.get(f"/api/v1/reels/{private.id}/", **self.auth(self.caro_token)).status_code, 403)

    def test_reel_like_save_view_comment_archive_report_hide_not_interested(self):
        reel = self.create_reel()
        self.assertEqual(self.post_json(f"/api/v1/reels/{reel.id}/like/", token=self.bob_token).status_code, 200)
        self.assertEqual(self.post_json(f"/api/v1/reels/{reel.id}/like/", token=self.bob_token).status_code, 200)
        self.assertEqual(ReelLike.objects.filter(reel=reel, user=self.bob).count(), 1)
        self.assertEqual(self.client.delete(f"/api/v1/reels/{reel.id}/like/", **self.auth(self.bob_token)).status_code, 200)
        self.assertEqual(self.post_json(f"/api/v1/reels/{reel.id}/save/", token=self.bob_token).status_code, 200)
        self.assertTrue(SavedReel.objects.filter(reel=reel, user=self.bob).exists())
        self.assertEqual(self.post_json(f"/api/v1/reels/{reel.id}/view/", {"watch_duration": 3, "completion_percentage": 91}, token=self.bob_token).status_code, 200)
        self.assertEqual(self.post_json(f"/api/v1/reels/{reel.id}/view/", {"watch_duration": 4}, token=self.bob_token).status_code, 200)
        self.assertEqual(ReelView.objects.filter(reel=reel, viewer=self.bob).count(), 1)
        self.assertEqual(self.post_json(f"/api/v1/reels/{reel.id}/comments/", {"text": "Great"}, token=self.bob_token).status_code, 201)
        reel.comments_enabled = False
        reel.save(update_fields=["comments_enabled"])
        self.assertEqual(self.post_json(f"/api/v1/reels/{reel.id}/comments/", {"text": "No"}, token=self.bob_token).status_code, 403)
        self.assertEqual(self.post_json(f"/api/v1/reels/{reel.id}/archive/").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/me/archived-reels/", **self.auth(self.alice_token)).json()["data"]["count"], 1)
        self.assertEqual(self.post_json(f"/api/v1/reels/{reel.id}/restore/").status_code, 200)
        self.assertEqual(self.post_json(f"/api/v1/reels/{reel.id}/report/", {"reason": "spam"}, token=self.bob_token).status_code, 200)
        self.assertTrue(ReelReport.objects.filter(reel=reel, reporter=self.bob).exists())
        self.assertEqual(self.post_json(f"/api/v1/reels/{reel.id}/hide/", token=self.bob_token).status_code, 200)
        self.assertEqual(self.post_json(f"/api/v1/reels/{reel.id}/not-interested/", token=self.caro_token).status_code, 200)

    def test_reel_owner_permissions_and_admin_moderation(self):
        reel = self.create_reel()
        self.assertEqual(self.client.patch(f"/api/v1/reels/{reel.id}/", data=json.dumps({"caption": "bad"}), content_type="application/json", **self.auth(self.bob_token)).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/v1/reels/{reel.id}/", **self.auth(self.bob_token)).status_code, 403)
        self.assertEqual(self.client.patch(f"/api/v1/reels/{reel.id}/", data=json.dumps({"caption": "new"}), content_type="application/json", **self.auth(self.alice_token)).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/admin/reels/", **self.auth(self.admin_token)).status_code, 200)
        self.assertEqual(self.post_json(f"/api/v1/admin/reels/{reel.id}/remove/", {"reason": "policy"}, token=self.admin_token).status_code, 200)
        reel.refresh_from_db()
        self.assertEqual(reel.status, Reel.STATUS_REMOVED)
        self.assertTrue(AdminAuditLog.objects.filter(admin_user=self.admin, action="reels_remove").exists())
        story = self.create_story()
        self.assertEqual(self.client.get("/api/v1/admin/stories/", **self.auth(self.admin_token)).status_code, 200)
        self.assertEqual(self.post_json(f"/api/v1/admin/stories/{story.id}/remove/", {"reason": "policy"}, token=self.admin_token).status_code, 200)
        story.refresh_from_db()
        self.assertEqual(story.status, Story.STATUS_REMOVED)
