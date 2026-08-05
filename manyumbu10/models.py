from datetime import timedelta
import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def normalize_phone_number(value: str, default_country_code: str = "255") -> str:
    raw = "".join(str(value or "").strip().replace("-", " ").replace("(", " ").replace(")", " ").split())
    if raw.startswith("00"):
        raw = "+" + raw[2:]
    elif raw.startswith("0"):
        raw = f"+{default_country_code}{raw[1:]}"
    elif raw.startswith(default_country_code):
        raw = f"+{raw}"
    elif raw.startswith("+"):
        pass
    elif raw.isdigit() and 8 <= len(raw) <= 15:
        raw = f"+{raw}"

    digits = raw[1:] if raw.startswith("+") else ""
    if not raw.startswith("+") or not digits.isdigit() or not 8 <= len(digits) <= 15:
        raise ValidationError("Enter a valid phone number in E.164 format.")
    return raw


class UserManager(BaseUserManager):
    def create_user(self, phone_number, email, username, full_name, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("Phone number is required.")
        if not email:
            raise ValueError("Email is required.")
        if not username:
            raise ValueError("Username is required.")
        normalized_phone = normalize_phone_number(phone_number)
        email = self.normalize_email(email)
        user = self.model(
            phone_number=normalized_phone,
            email=email,
            username=username.strip().lower(),
            full_name=full_name.strip(),
            **extra_fields,
        )
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, email, username, full_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_verified", True)
        extra_fields.setdefault("date_of_birth", "1990-01-01")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(phone_number, email, username, full_name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(primary_key=True, max_length=20)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    profile_picture = models.ImageField(upload_to="profiles/", null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_creator = models.BooleanField(default=False)
    is_business = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["email", "username", "full_name"]

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["username"]),
            models.Index(fields=["created_at"]),
        ]

    def clean(self):
        super().clean()
        self.phone_number = normalize_phone_number(self.phone_number)
        self.email = User.objects.normalize_email(self.email)
        self.username = self.username.strip().lower()

    def __str__(self):
        return f"{self.username} ({self.phone_number})"


class UserProfile(models.Model):
    ACCOUNT_PERSONAL = "personal"
    ACCOUNT_CREATOR = "creator"
    ACCOUNT_BUSINESS = "business"
    ACCOUNT_TYPES = [
        (ACCOUNT_PERSONAL, "Personal"),
        (ACCOUNT_CREATOR, "Creator"),
        (ACCOUNT_BUSINESS, "Business"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    bio = models.CharField(max_length=280, blank=True)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    cover_photo = models.ImageField(upload_to="covers/", null=True, blank=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default=ACCOUNT_PERSONAL)
    is_private = models.BooleanField(default=False)
    posts_count = models.PositiveIntegerField(default=0)
    reels_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user_id}"

class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    refresh_token_hash = models.CharField(max_length=128, unique=True)
    device_name = models.CharField(max_length=120, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["user", "revoked_at"]), models.Index(fields=["created_at"])]


class EmailVerificationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_verification_codes")
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    created_ip = models.GenericIPAddressField(null=True, blank=True)
    created_device = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["user", "used_at", "expires_at"]), models.Index(fields=["created_at"])]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @classmethod
    def expiry_time(cls):
        return timezone.now() + timedelta(minutes=10)


class PasswordResetCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_codes")
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["user", "used_at", "expires_at"])]


class GoogleAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="google_account", null=True, blank=True)
    google_sub = models.CharField(max_length=255, unique=True)
    email = models.EmailField()
    is_verified_email = models.BooleanField(default=False)
    pending_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class UserPrivacySettings(models.Model):
    DOB_HIDDEN = "hidden"
    DOB_MONTH_DAY = "month_day"
    DOB_FULL = "full"
    DOB_VISIBILITY = [
        (DOB_HIDDEN, "Hidden"),
        (DOB_MONTH_DAY, "Month and day"),
        (DOB_FULL, "Full date"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="privacy_settings")
    show_in_suggestions = models.BooleanField(default=True)
    phone_discoverable = models.BooleanField(default=False)
    dob_visibility = models.CharField(max_length=20, choices=DOB_VISIBILITY, default=DOB_HIDDEN)
    profile_details_public = models.BooleanField(default=True)
    online_status_visible = models.BooleanField(default=True)
    who_can_message_me = models.CharField(max_length=30, default="everyone")
    who_can_add_to_conversations = models.CharField(max_length=30, default="people_i_follow")
    show_online_status = models.CharField(max_length=30, default="everyone")
    show_last_seen = models.CharField(max_length=30, default="people_i_follow")
    send_read_receipts = models.BooleanField(default=True)
    show_typing_indicator = models.BooleanField(default=True)
    show_recording_indicator = models.BooleanField(default=True)
    allow_message_requests = models.BooleanField(default=True)
    allow_forwarded_messages_from_unknown_users = models.BooleanField(default=False)
    who_can_call_me = models.CharField(max_length=40, default="everyone")
    allow_voice_calls = models.BooleanField(default=True)
    allow_video_calls = models.BooleanField(default=True)
    show_call_notifications = models.BooleanField(default=True)
    silence_calls_from_unknown_users = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following_edges")
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name="follower_edges")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["follower", "following"], name="unique_follow"),
            models.CheckConstraint(condition=~models.Q(follower=models.F("following")), name="prevent_self_follow"),
        ]
        indexes = [models.Index(fields=["follower", "created_at"]), models.Index(fields=["following", "created_at"])]


class FollowRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_CANCELED = "canceled"
    STATUSES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_CANCELED, "Canceled"),
    ]

    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_follow_requests")
    target = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_follow_requests")
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_PENDING)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["requester", "target", "status"], name="unique_follow_request_status"),
            models.CheckConstraint(condition=~models.Q(requester=models.F("target")), name="prevent_self_follow_request"),
        ]
        indexes = [models.Index(fields=["requester", "status"]), models.Index(fields=["target", "status"])]


class BlockedUser(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocked_edges")
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocked_by_edges")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="unique_block"),
            models.CheckConstraint(condition=~models.Q(blocker=models.F("blocked")), name="prevent_self_block"),
        ]
        indexes = [models.Index(fields=["blocker", "created_at"]), models.Index(fields=["blocked"])]


class RestrictedUser(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="restricted_edges")
    restricted = models.ForeignKey(User, on_delete=models.CASCADE, related_name="restricted_by_edges")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "restricted"], name="unique_restriction"),
            models.CheckConstraint(condition=~models.Q(owner=models.F("restricted")), name="prevent_self_restrict"),
        ]


class MutedUser(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="muted_edges")
    muted = models.ForeignKey(User, on_delete=models.CASCADE, related_name="muted_by_edges")
    mute_posts = models.BooleanField(default=False)
    mute_stories = models.BooleanField(default=False)
    mute_messages = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "muted"], name="unique_mute"),
            models.CheckConstraint(condition=~models.Q(owner=models.F("muted")), name="prevent_self_mute"),
        ]
        indexes = [models.Index(fields=["owner", "created_at"])]


class CloseFriend(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="close_friend_edges")
    friend = models.ForeignKey(User, on_delete=models.CASCADE, related_name="close_friend_of_edges")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "friend"], name="unique_close_friend"),
            models.CheckConstraint(condition=~models.Q(owner=models.F("friend")), name="prevent_self_close_friend"),
        ]
        indexes = [models.Index(fields=["owner", "created_at"])]


class Hashtag(models.Model):
    name = models.CharField(max_length=80, unique=True)
    display_name = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["name"])]


class Post(models.Model):
    TYPE_TEXT = "text"
    TYPE_IMAGE = "image"
    TYPE_VIDEO = "video"
    TYPES = [(TYPE_TEXT, "Text"), (TYPE_IMAGE, "Image"), (TYPE_VIDEO, "Video")]
    AUDIENCE_PUBLIC = "public"
    AUDIENCE_FOLLOWERS = "followers"
    AUDIENCE_CLOSE_FRIENDS = "close_friends"
    AUDIENCE_SELECTED = "selected"
    AUDIENCE_ONLY_ME = "only_me"
    AUDIENCES = [(AUDIENCE_PUBLIC, "Public"), (AUDIENCE_FOLLOWERS, "Followers"), (AUDIENCE_CLOSE_FRIENDS, "Close friends"), (AUDIENCE_SELECTED, "Selected users"), (AUDIENCE_ONLY_ME, "Only me")]
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"
    STATUS_REMOVED = "removed"
    STATUS_DELETED = "deleted"
    STATUSES = [(STATUS_DRAFT, "Draft"), (STATUS_PUBLISHED, "Published"), (STATUS_ARCHIVED, "Archived"), (STATUS_REMOVED, "Removed"), (STATUS_DELETED, "Deleted")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    caption = models.TextField(blank=True, max_length=2200)
    post_type = models.CharField(max_length=20, choices=TYPES, default=TYPE_TEXT)
    audience = models.CharField(max_length=20, choices=AUDIENCES, default=AUDIENCE_PUBLIC)
    comments_enabled = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_PUBLISHED)
    location_name = models.CharField(max_length=140, blank=True)
    is_edited = models.BooleanField(default=False)
    share_count = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["author", "status", "published_at"]), models.Index(fields=["audience", "status", "published_at"]), models.Index(fields=["created_at"])]


class PostMedia(models.Model):
    MEDIA_IMAGE = "image"
    MEDIA_VIDEO = "video"
    TYPES = [(MEDIA_IMAGE, "Image"), (MEDIA_VIDEO, "Video")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="media")
    file = models.FileField(upload_to="posts/")
    media_url = models.URLField(blank=True)
    secure_url = models.URLField(blank=True)
    media_type = models.CharField(max_length=20, choices=TYPES)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    display_order = models.PositiveSmallIntegerField(default=0)
    thumbnail = models.FileField(upload_to="post-thumbnails/", null=True, blank=True)
    upload_provider_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "display_order"], name="unique_post_media_order")]
        indexes = [models.Index(fields=["post", "display_order"])]


class PostAudienceUser(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="selected_audience")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="selected_posts")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "user"], name="unique_post_selected_audience")]


class PostTag(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="tagged_users")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tagged_posts")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "user"], name="unique_post_tag")]


class PostMention(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="mentions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_mentions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "user"], name="unique_post_mention")]


class PostHashtag(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="hashtags")
    hashtag = models.ForeignKey(Hashtag, on_delete=models.CASCADE, related_name="post_links")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "hashtag"], name="unique_post_hashtag")]


class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "user"], name="unique_post_like")]
        indexes = [models.Index(fields=["post", "created_at"])]


class SavedPost(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="saves")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_posts")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "user"], name="unique_saved_post")]
        indexes = [models.Index(fields=["user", "created_at"])]


class HiddenPost(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="hidden_by")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="hidden_posts")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "user"], name="unique_hidden_post")]


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="replies", null=True, blank=True)
    text = models.TextField(max_length=1000)
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["post", "created_at"]), models.Index(fields=["parent", "created_at"])]


class CommentLike(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comment_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["comment", "user"], name="unique_comment_like")]


class CommentMention(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="mentions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comment_mentions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["comment", "user"], name="unique_comment_mention")]


class Notification(models.Model):
    TYPE_POST_LIKED = "post_liked"
    TYPE_POST_COMMENTED = "post_commented"
    TYPE_COMMENT_REPLIED = "comment_replied"
    TYPE_COMMENT_LIKED = "comment_liked"
    TYPE_POST_MENTION = "post_mention"
    TYPE_COMMENT_MENTION = "comment_mention"
    TYPE_POST_TAG = "post_tag"
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications_created")
    notification_type = models.CharField(max_length=60)
    object_type = models.CharField(max_length=60, blank=True)
    object_uuid = models.CharField(max_length=80, blank=True)
    safe_payload = models.JSONField(default=dict, blank=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    message = models.CharField(max_length=180, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    seen_at = models.DateTimeField(null=True, blank=True)
    push_status = models.CharField(max_length=30, default="not_configured")
    email_status = models.CharField(max_length=30, default="not_sent")
    priority = models.CharField(max_length=20, default="normal")
    grouping_key = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["recipient", "is_read", "created_at"])]


class PostReport(models.Model):
    REASONS = [("spam", "Spam"), ("harassment", "Harassment"), ("hate", "Hate or abusive content"), ("nudity", "Nudity or sexual content"), ("violence", "Violence"), ("scam", "Scam or fraud"), ("false_information", "False information"), ("intellectual_property", "Intellectual property"), ("other", "Other")]
    STATUS_PENDING = "pending"
    STATUS_REVIEWED = "reviewed"
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_reports")
    reason = models.CharField(max_length=40, choices=REASONS)
    details = models.TextField(blank=True, max_length=1000)
    status = models.CharField(max_length=20, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "reporter", "reason"], name="unique_post_report_reason")]


class AdminAuditLog(models.Model):
    admin_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="admin_audit_logs")
    action = models.CharField(max_length=120)
    target = models.CharField(max_length=255)
    reason = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["admin_user", "created_at"]), models.Index(fields=["action"])]

class Story(models.Model):
    TYPE_TEXT = "text"
    TYPE_IMAGE = "image"
    TYPE_VIDEO = "video"
    TYPES = [(TYPE_TEXT, "Text"), (TYPE_IMAGE, "Image"), (TYPE_VIDEO, "Video")]
    AUDIENCE_EVERYONE = "everyone"
    AUDIENCE_FOLLOWERS = "followers"
    AUDIENCE_CLOSE_FRIENDS = "close_friends"
    AUDIENCE_SELECTED = "selected"
    AUDIENCE_HIDE_SELECTED = "hide_selected"
    AUDIENCES = [(AUDIENCE_EVERYONE, "Everyone"), (AUDIENCE_FOLLOWERS, "Followers"), (AUDIENCE_CLOSE_FRIENDS, "Close friends"), (AUDIENCE_SELECTED, "Selected users"), (AUDIENCE_HIDE_SELECTED, "Hide selected users")]
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_EXPIRED = "expired"
    STATUS_DELETED = "deleted"
    STATUS_REMOVED = "removed"
    STATUSES = [(STATUS_DRAFT, "Draft"), (STATUS_PUBLISHED, "Published"), (STATUS_EXPIRED, "Expired"), (STATUS_DELETED, "Deleted"), (STATUS_REMOVED, "Removed")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="stories")
    story_type = models.CharField(max_length=20, choices=TYPES, default=TYPE_TEXT)
    caption = models.TextField(blank=True, max_length=1000)
    audience = models.CharField(max_length=20, choices=AUDIENCES, default=AUDIENCE_EVERYONE)
    background_style = models.CharField(max_length=120, blank=True)
    link_url = models.URLField(blank=True)
    location_name = models.CharField(max_length=140, blank=True)
    sticker_metadata = models.JSONField(default=dict, blank=True)
    replies_enabled = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_PUBLISHED)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["author", "status", "expires_at"]), models.Index(fields=["audience", "status", "expires_at"])]


class StoryMedia(models.Model):
    story = models.OneToOneField(Story, on_delete=models.CASCADE, related_name="media")
    file = models.FileField(upload_to="stories/")
    media_type = models.CharField(max_length=20)
    media_url = models.URLField(blank=True)
    secure_url = models.URLField(blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    thumbnail = models.FileField(upload_to="story-thumbnails/", null=True, blank=True)
    upload_provider_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class StoryAudienceUser(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="selected_audience")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="selected_stories")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["story", "user"], name="unique_story_audience_user")]


class StoryHiddenUser(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="hidden_users")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="hidden_from_stories")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["story", "user"], name="unique_story_hidden_user")]


class StoryMention(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="mentions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="story_mentions")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["story", "user"], name="unique_story_mention")]


class StoryHashtag(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="hashtags")
    hashtag = models.ForeignKey(Hashtag, on_delete=models.CASCADE, related_name="story_links")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["story", "hashtag"], name="unique_story_hashtag")]


class StoryView(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="views")
    viewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="story_views")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["story", "viewer"], name="unique_story_view")]
        indexes = [models.Index(fields=["story", "created_at"])]


class StoryReaction(models.Model):
    REACTIONS = [("like", "Like"), ("laugh", "Laugh"), ("surprise", "Surprise"), ("sad", "Sad"), ("fire", "Fire"), ("celebration", "Celebration")]
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="story_reactions")
    reaction = models.CharField(max_length=20, choices=REACTIONS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["story", "user"], name="unique_story_reaction")]


class StoryReply(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="story_replies")
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)


class StoryPoll(models.Model):
    story = models.OneToOneField(Story, on_delete=models.CASCADE, related_name="poll")
    question = models.CharField(max_length=180)
    show_results = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class StoryPollOption(models.Model):
    poll = models.ForeignKey(StoryPoll, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=80)
    display_order = models.PositiveSmallIntegerField(default=0)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["poll", "display_order"], name="unique_story_poll_option_order")]


class StoryPollVote(models.Model):
    poll = models.ForeignKey(StoryPoll, on_delete=models.CASCADE, related_name="votes")
    option = models.ForeignKey(StoryPollOption, on_delete=models.CASCADE, related_name="votes")
    voter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="story_poll_votes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["poll", "voter"], name="unique_story_poll_vote")]


class StoryHighlight(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="story_highlights")
    title = models.CharField(max_length=60)
    cover_image = models.ImageField(upload_to="highlight-covers/", null=True, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        indexes = [models.Index(fields=["owner", "display_order"])]


class StoryHighlightItem(models.Model):
    highlight = models.ForeignKey(StoryHighlight, on_delete=models.CASCADE, related_name="items")
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="highlight_items")
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["highlight", "story"], name="unique_highlight_story")]


class StoryReport(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="story_reports")
    reason = models.CharField(max_length=40, choices=PostReport.REASONS)
    details = models.TextField(blank=True, max_length=1000)
    status = models.CharField(max_length=20, default=PostReport.STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["story", "reporter", "reason"], name="unique_story_report_reason")]


class Reel(models.Model):
    AUDIENCES = Post.AUDIENCES
    STATUS_DRAFT = "draft"
    STATUS_PROCESSING = "processing"
    STATUS_PUBLISHED = "published"
    STATUS_FAILED = "failed"
    STATUS_ARCHIVED = "archived"
    STATUS_REMOVED = "removed"
    STATUS_DELETED = "deleted"
    PROCESSING_PENDING = "pending"
    PROCESSING_READY = "ready"
    PROCESSING_FAILED = "failed"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reels")
    caption = models.TextField(blank=True, max_length=2200)
    audience = models.CharField(max_length=20, choices=AUDIENCES, default=Post.AUDIENCE_PUBLIC)
    comments_enabled = models.BooleanField(default=True)
    status = models.CharField(max_length=20, default=STATUS_PUBLISHED)
    location_name = models.CharField(max_length=140, blank=True)
    video = models.FileField(upload_to="reels/", null=True, blank=True)
    cover_image = models.ImageField(upload_to="reel-covers/", null=True, blank=True)
    video_url = models.URLField(blank=True)
    thumbnail_url = models.URLField(blank=True)
    duration = models.FloatField(null=True, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    aspect_ratio = models.CharField(max_length=20, blank=True)
    processing_status = models.CharField(max_length=20, default=PROCESSING_PENDING)
    view_count = models.PositiveIntegerField(default=0)
    share_count = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        indexes = [models.Index(fields=["author", "status", "published_at"]), models.Index(fields=["audience", "status", "published_at"])]


class ReelAudienceUser(models.Model):
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name="selected_audience")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="selected_reels")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["reel", "user"], name="unique_reel_audience_user")]


class ReelTag(models.Model):
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name="tagged_users")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tagged_reels")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["reel", "user"], name="unique_reel_tag")]


class ReelMention(models.Model):
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name="mentions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reel_mentions")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["reel", "user"], name="unique_reel_mention")]


class ReelHashtag(models.Model):
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name="hashtags")
    hashtag = models.ForeignKey(Hashtag, on_delete=models.CASCADE, related_name="reel_links")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["reel", "hashtag"], name="unique_reel_hashtag")]


class ReelLike(models.Model):
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reel_likes")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["reel", "user"], name="unique_reel_like")]


class SavedReel(models.Model):
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name="saves")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_reels")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["reel", "user"], name="unique_saved_reel")]


class ReelView(models.Model):
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name="views")
    viewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reel_views")
    watch_duration = models.FloatField(default=0)
    completion_percentage = models.FloatField(default=0)
    completed = models.BooleanField(default=False)
    replay_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["reel", "viewer"], name="unique_reel_view")]


class HiddenReel(models.Model):
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name="hidden_by")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="hidden_reels")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["reel", "user"], name="unique_hidden_reel")]


class ReelNotInterested(models.Model):
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name="not_interested_by")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="not_interested_reels")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["reel", "user"], name="unique_reel_not_interested")]


class ReelComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reel_comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="replies", null=True, blank=True)
    text = models.TextField(max_length=1000)
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ReelReport(models.Model):
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reel_reports")
    reason = models.CharField(max_length=40, choices=PostReport.REASONS)
    details = models.TextField(blank=True, max_length=1000)
    status = models.CharField(max_length=20, default=PostReport.STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["reel", "reporter", "reason"], name="unique_reel_report_reason")]


class Conversation(models.Model):
    TYPE_PRIVATE = "private"
    TYPES = [(TYPE_PRIVATE, "Private")]
    STATUS_ACTIVE = "active"
    STATUS_DELETED = "deleted"
    STATUSES = [(STATUS_ACTIVE, "Active"), (STATUS_DELETED, "Deleted")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation_type = models.CharField(max_length=20, choices=TYPES, default=TYPE_PRIVATE)
    private_pair_key = models.CharField(max_length=80, unique=True)
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_ACTIVE)
    last_message = models.ForeignKey("Message", on_delete=models.SET_NULL, null=True, blank=True, related_name="last_for_conversations")
    last_message_at = models.DateTimeField(null=True, blank=True)
    soft_deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["conversation_type", "last_message_at"]), models.Index(fields=["status", "updated_at"])]


class ConversationParticipant(models.Model):
    REQUEST_NONE = "none"
    REQUEST_PENDING = "pending"
    REQUEST_ACCEPTED = "accepted"
    REQUEST_REJECTED = "rejected"
    REQUEST_DELETED = "deleted"
    REQUEST_SPAM = "spam"
    REQUEST_STATES = [(REQUEST_NONE, "None"), (REQUEST_PENDING, "Pending"), (REQUEST_ACCEPTED, "Accepted"), (REQUEST_REJECTED, "Rejected"), (REQUEST_DELETED, "Deleted"), (REQUEST_SPAM, "Spam")]
    NOTIFY_ALL = "all"
    NOTIFY_MENTIONS = "mentions"
    NOTIFY_NONE = "none"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversation_participations")
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_message = models.ForeignKey("Message", on_delete=models.SET_NULL, null=True, blank=True, related_name="last_read_by")
    last_read_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    muted_until = models.DateTimeField(null=True, blank=True)
    marked_unread = models.BooleanField(default=False)
    cleared_before = models.DateTimeField(null=True, blank=True)
    request_state = models.CharField(max_length=20, choices=REQUEST_STATES, default=REQUEST_NONE)
    notification_preference = models.CharField(max_length=20, default=NOTIFY_ALL)
    keep_archived = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["conversation", "user"], name="unique_conversation_participant")]
        indexes = [models.Index(fields=["user", "archived_at", "updated_at"]), models.Index(fields=["conversation", "request_state"])]


class Message(models.Model):
    TYPE_TEXT = "text"
    TYPE_IMAGE = "image"
    TYPE_VIDEO = "video"
    TYPE_DOCUMENT = "document"
    TYPE_AUDIO = "audio"
    TYPE_VOICE_NOTE = "voice_note"
    TYPE_LOCATION = "location"
    TYPE_CONTACT = "contact"
    TYPE_POST_SHARE = "post_share"
    TYPE_REEL_SHARE = "reel_share"
    TYPE_STORY_REPLY = "story_reply"
    TYPE_SYSTEM = "system"
    TYPES = [(TYPE_TEXT, "Text"), (TYPE_IMAGE, "Image"), (TYPE_VIDEO, "Video"), (TYPE_DOCUMENT, "Document"), (TYPE_AUDIO, "Audio"), (TYPE_VOICE_NOTE, "Voice note"), (TYPE_LOCATION, "Location"), (TYPE_CONTACT, "Contact"), (TYPE_POST_SHARE, "Post share"), (TYPE_REEL_SHARE, "Reel share"), (TYPE_STORY_REPLY, "Story reply"), (TYPE_SYSTEM, "System")]
    STATUS_SENT = "sent"
    STATUS_DELIVERED = "delivered"
    STATUS_READ = "read"
    STATUS_FAILED = "failed"
    STATUS_DELETED = "deleted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    message_type = models.CharField(max_length=30, choices=TYPES, default=TYPE_TEXT)
    text = models.TextField(blank=True, max_length=5000)
    reply_to = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies")
    forwarded_from = models.JSONField(default=dict, blank=True)
    shared_content = models.JSONField(default=dict, blank=True)
    location_payload = models.JSONField(default=dict, blank=True)
    contact_payload = models.JSONField(default=dict, blank=True)
    client_message_id = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, default=STATUS_SENT)
    is_forwarded = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_for_everyone_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["sender", "client_message_id"], condition=~models.Q(client_message_id=""), name="unique_message_client_id_per_sender")]
        indexes = [models.Index(fields=["conversation", "created_at"]), models.Index(fields=["sender", "created_at"]), models.Index(fields=["message_type", "created_at"])]


class MessageAttachment(models.Model):
    KIND_IMAGE = "image"
    KIND_VIDEO = "video"
    KIND_DOCUMENT = "document"
    KIND_AUDIO = "audio"
    KIND_VOICE_NOTE = "voice_note"
    KINDS = [(KIND_IMAGE, "Image"), (KIND_VIDEO, "Video"), (KIND_DOCUMENT, "Document"), (KIND_AUDIO, "Audio"), (KIND_VOICE_NOTE, "Voice note")]
    PROCESSING_PENDING = "pending"
    PROCESSING_READY = "ready"
    PROCESSING_FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="message_attachments")
    file = models.FileField(upload_to="messages/", null=True, blank=True)
    kind = models.CharField(max_length=30, choices=KINDS)
    file_name = models.CharField(max_length=180)
    mime_type = models.CharField(max_length=120)
    file_size = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)
    thumbnail = models.FileField(upload_to="message-thumbnails/", null=True, blank=True)
    waveform = models.JSONField(default=list, blank=True)
    processing_status = models.CharField(max_length=20, default=PROCESSING_READY)
    malware_scan_status = models.CharField(max_length=20, default="pending")
    upload_provider_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["message", "kind"]), models.Index(fields=["owner", "created_at"])]


class MessageDeletion(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="deleted_for")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="message_deletions")
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["message", "user"], name="unique_message_delete_for_user")]


class MessageReaction(models.Model):
    REACTIONS = [("like", "Like"), ("love", "Love"), ("laugh", "Laugh"), ("surprise", "Surprise"), ("sad", "Sad"), ("celebration", "Celebration")]
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="message_reactions")
    reaction = models.CharField(max_length=20, choices=REACTIONS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["message", "user"], name="unique_message_reaction")]


class MessageReadReceipt(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="read_receipts")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="message_read_receipts")
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["message", "user"], name="unique_message_read_receipt")]
        indexes = [models.Index(fields=["user", "read_at"])]


class MessageDeliveryReceipt(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="delivery_receipts")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="message_delivery_receipts")
    delivered_at = models.DateTimeField(auto_now_add=True)
    device_id = models.CharField(max_length=120, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["message", "user", "device_id"], name="unique_message_delivery_receipt")]


class MessageStar(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="stars")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="message_stars")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["message", "user"], name="unique_message_star")]
        indexes = [models.Index(fields=["user", "created_at"])]


class MessagePin(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="pins")
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="pins")
    pinned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="message_pins")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["message", "conversation"], name="unique_conversation_message_pin")]
        indexes = [models.Index(fields=["conversation", "created_at"])]


class ConversationMute(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="mute_records")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversation_mutes")
    muted_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["conversation", "user"], name="unique_conversation_mute")]


class ConversationArchive(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="archive_records")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversation_archives")
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["conversation", "user"], name="unique_conversation_archive")]


class ConversationClearState(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="clear_states")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversation_clear_states")
    cleared_before = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["conversation", "user"], name="unique_conversation_clear_state")]


class MessageRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_DELETED = "deleted"
    STATUS_SPAM = "spam"
    STATUSES = [(STATUS_PENDING, "Pending"), (STATUS_ACCEPTED, "Accepted"), (STATUS_REJECTED, "Rejected"), (STATUS_DELETED, "Deleted"), (STATUS_SPAM, "Spam")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name="message_request")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_message_requests")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_message_requests")
    preview_text = models.CharField(max_length=280, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_PENDING)
    responded_at = models.DateTimeField(null=True, blank=True)
    spam_score = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["sender", "receiver", "status"], name="unique_message_request_state")]
        indexes = [models.Index(fields=["receiver", "status", "created_at"]), models.Index(fields=["sender", "receiver"])]


class MessageReport(models.Model):
    REASONS = PostReport.REASONS
    STATUS_PENDING = "pending"
    STATUS_UNDER_REVIEW = "under_review"
    STATUS_RESOLVED = "resolved"
    STATUS_REJECTED = "rejected"
    STATUSES = [(STATUS_PENDING, "Pending"), (STATUS_UNDER_REVIEW, "Under review"), (STATUS_RESOLVED, "Resolved"), (STATUS_REJECTED, "Rejected")]
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="message_reports")
    reason = models.CharField(max_length=40, choices=REASONS)
    details = models.TextField(blank=True, max_length=1000)
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_PENDING)
    context_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["message", "reporter", "reason"], name="unique_message_report_reason")]
        indexes = [models.Index(fields=["status", "created_at"])]


class ConversationReport(models.Model):
    REASONS = PostReport.REASONS
    STATUS_PENDING = "pending"
    STATUS_UNDER_REVIEW = "under_review"
    STATUS_RESOLVED = "resolved"
    STATUS_REJECTED = "rejected"
    STATUSES = MessageReport.STATUSES
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversation_reports")
    reason = models.CharField(max_length=40, choices=REASONS)
    details = models.TextField(blank=True, max_length=1000)
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_PENDING)
    context_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["conversation", "reporter", "reason"], name="unique_conversation_report_reason")]
        indexes = [models.Index(fields=["status", "created_at"])]


class UserPresence(models.Model):
    STATE_OFFLINE = "offline"
    STATE_ONLINE = "online"
    STATE_RECENTLY_ACTIVE = "recently_active"
    STATES = [(STATE_OFFLINE, "Offline"), (STATE_ONLINE, "Online"), (STATE_RECENTLY_ACTIVE, "Recently active")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="presence")
    state = models.CharField(max_length=30, choices=STATES, default=STATE_OFFLINE)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class UserDevice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="devices")
    device_id = models.CharField(max_length=120)
    device_name = models.CharField(max_length=120, blank=True)
    platform = models.CharField(max_length=40, blank=True)
    push_token = models.CharField(max_length=255, blank=True)
    notification_preferences = models.JSONField(default=dict, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "device_id"], name="unique_user_device")]
        indexes = [models.Index(fields=["user", "revoked_at"])]


class WebSocketSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="websocket_sessions")
    channel_name = models.CharField(max_length=255)
    device_id = models.CharField(max_length=120, blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "disconnected_at"]), models.Index(fields=["channel_name"])]



class Group(models.Model):
    PRIVACY_PRIVATE = "private"
    PRIVACY_INVITE_ONLY = "invite_only"
    PRIVACY_PUBLIC = "public"
    PRIVACIES = [(PRIVACY_PRIVATE, "Private"), (PRIVACY_INVITE_ONLY, "Invite only"), (PRIVACY_PUBLIC, "Public")]
    ROLE_OWNER = "owner"
    ROLE_ADMIN = "admin"
    ROLE_MODERATOR = "moderator"
    ROLE_MEMBER = "member"
    ROLE_CHOICES = [(ROLE_OWNER, "Owner"), (ROLE_ADMIN, "Administrator"), (ROLE_MODERATOR, "Moderator"), (ROLE_MEMBER, "Member")]
    PERM_EVERYONE = "everyone"
    PERM_MODERATORS = "moderators"
    PERM_ADMINS = "admins"
    PERM_OWNER = "owner"
    PERM_CHOICES = [(PERM_EVERYONE, "Everyone"), (PERM_MODERATORS, "Moderators and admins"), (PERM_ADMINS, "Admins"), (PERM_OWNER, "Owner")]
    JOIN_DIRECT = "direct"
    JOIN_APPROVAL = "approval"
    JOIN_INVITE = "invite"
    JOIN_CHOICES = [(JOIN_DIRECT, "Direct"), (JOIN_APPROVAL, "Approval"), (JOIN_INVITE, "Invite")]
    STATUS_ACTIVE = "active"
    STATUS_SUSPENDED = "suspended"
    STATUS_DELETED = "deleted"
    STATUS_ARCHIVED = "archived"
    STATUSES = [(STATUS_ACTIVE, "Active"), (STATUS_SUSPENDED, "Suspended"), (STATUS_DELETED, "Deleted"), (STATUS_ARCHIVED, "Archived")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, max_length=1000)
    image = models.ImageField(upload_to="groups/", null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_groups")
    privacy = models.CharField(max_length=20, choices=PRIVACIES, default=PRIVACY_PRIVATE)
    member_count = models.PositiveIntegerField(default=0)
    maximum_members = models.PositiveIntegerField(default=256)
    who_can_join = models.CharField(max_length=20, choices=JOIN_CHOICES, default=JOIN_INVITE)
    who_can_send_messages = models.CharField(max_length=20, choices=PERM_CHOICES, default=PERM_EVERYONE)
    who_can_edit_info = models.CharField(max_length=20, choices=PERM_CHOICES, default=PERM_ADMINS)
    who_can_add_members = models.CharField(max_length=20, choices=PERM_CHOICES, default=PERM_ADMINS)
    who_can_approve_members = models.CharField(max_length=20, choices=PERM_CHOICES, default=PERM_ADMINS)
    who_can_create_invites = models.CharField(max_length=20, choices=PERM_CHOICES, default=PERM_ADMINS)
    who_can_pin_messages = models.CharField(max_length=20, choices=PERM_CHOICES, default=PERM_MODERATORS)
    who_can_mention_everyone = models.CharField(max_length=20, choices=PERM_CHOICES, default=PERM_ADMINS)
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_ACTIVE)
    last_message_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        indexes = [models.Index(fields=["privacy", "status", "updated_at"]), models.Index(fields=["owner", "created_at"]), models.Index(fields=["last_message_at"])]


class GroupRole(models.Model):
    name = models.CharField(max_length=20, unique=True)
    permissions = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class GroupSettings(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="settings")
    require_join_approval = models.BooleanField(default=False)
    allow_invitation_links = models.BooleanField(default=True)
    allow_member_invites = models.BooleanField(default=False)
    message_rate_limit_per_minute = models.PositiveIntegerField(default=30)
    mention_everyone_rate_limit_per_day = models.PositiveIntegerField(default=3)
    keep_archived_on_new_message = models.BooleanField(default=False)
    notification_overrides = models.JSONField(default=dict, blank=True)
    who_can_start_calls = models.CharField(max_length=20, choices=Group.PERM_CHOICES, default=Group.PERM_ADMINS)
    voice_calls_enabled = models.BooleanField(default=True)
    video_calls_enabled = models.BooleanField(default=True)
    maximum_call_participants = models.PositiveIntegerField(default=16)
    call_join_requires_approval = models.BooleanField(default=False)
    allow_member_call_invites = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class GroupMember(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_LEFT = "left"
    STATUS_REMOVED = "removed"
    STATUS_BANNED = "banned"
    STATUSES = [(STATUS_ACTIVE, "Active"), (STATUS_LEFT, "Left"), (STATUS_REMOVED, "Removed"), (STATUS_BANNED, "Banned")]
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_memberships")
    role = models.CharField(max_length=20, choices=Group.ROLE_CHOICES, default=Group.ROLE_MEMBER)
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_ACTIVE)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_message = models.ForeignKey("GroupMessage", on_delete=models.SET_NULL, null=True, blank=True, related_name="last_read_by_members")
    last_read_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    muted_until = models.DateTimeField(null=True, blank=True)
    cleared_before = models.DateTimeField(null=True, blank=True)
    marked_unread = models.BooleanField(default=False)
    notification_preference = models.CharField(max_length=20, default="all")
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["group", "user"], name="unique_group_member")]
        indexes = [models.Index(fields=["group", "role", "status"]), models.Index(fields=["user", "status", "updated_at"])]


class GroupInvitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="invitations")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_group_invitations")
    token_hash = models.CharField(max_length=128, unique=True)
    token_preview = models.CharField(max_length=16, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    use_count = models.PositiveIntegerField(default=0)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=["group", "revoked_at", "expires_at"])]


class GroupJoinRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CANCELED = "canceled"
    STATUSES = [(STATUS_PENDING, "Pending"), (STATUS_APPROVED, "Approved"), (STATUS_REJECTED, "Rejected"), (STATUS_CANCELED, "Canceled")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="join_requests")
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_join_requests")
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_PENDING)
    decided_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="decided_group_join_requests")
    decided_at = models.DateTimeField(null=True, blank=True)
    message = models.CharField(max_length=280, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["group", "requester", "status"], name="unique_group_join_request_state")]
        indexes = [models.Index(fields=["group", "status", "created_at"])]


class GroupBan(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="bans")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_bans")
    banned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="issued_group_bans")
    reason = models.CharField(max_length=280, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["group", "user"], name="unique_group_ban")]


class GroupRestriction(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="restrictions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_restrictions")
    restricted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="issued_group_restrictions")
    restrict_messages = models.BooleanField(default=True)
    restrict_media = models.BooleanField(default=False)
    restrict_links = models.BooleanField(default=False)
    reason = models.CharField(max_length=280, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["group", "user"], name="unique_group_restriction")]


class GroupMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_group_messages")
    message_type = models.CharField(max_length=30, choices=Message.TYPES, default=Message.TYPE_TEXT)
    text = models.TextField(blank=True, max_length=5000)
    reply_to = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies")
    client_message_id = models.CharField(max_length=80, blank=True)
    shared_content = models.JSONField(default=dict, blank=True)
    location_payload = models.JSONField(default=dict, blank=True)
    contact_payload = models.JSONField(default=dict, blank=True)
    is_forwarded = models.BooleanField(default=False)
    forwarded_from = models.JSONField(default=dict, blank=True)
    mentioned_usernames = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, default=Message.STATUS_SENT)
    is_system = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_for_everyone_at = models.DateTimeField(null=True, blank=True)
    removed_by_moderator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="moderated_group_messages")
    moderation_reason = models.CharField(max_length=280, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["sender", "client_message_id"], condition=~models.Q(client_message_id=""), name="unique_group_message_client_id")]
        indexes = [models.Index(fields=["group", "created_at"]), models.Index(fields=["sender", "created_at"])]


class GroupMessageAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(GroupMessage, on_delete=models.CASCADE, related_name="attachments")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_message_attachments")
    file = models.FileField(upload_to="group-messages/", null=True, blank=True)
    kind = models.CharField(max_length=30, choices=MessageAttachment.KINDS)
    file_name = models.CharField(max_length=180)
    mime_type = models.CharField(max_length=120)
    file_size = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)
    thumbnail = models.FileField(upload_to="group-message-thumbnails/", null=True, blank=True)
    waveform = models.JSONField(default=list, blank=True)
    processing_status = models.CharField(max_length=20, default=MessageAttachment.PROCESSING_READY)
    malware_scan_status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)


class GroupMessageReaction(models.Model):
    message = models.ForeignKey(GroupMessage, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_message_reactions")
    reaction = models.CharField(max_length=20, choices=MessageReaction.REACTIONS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["message", "user"], name="unique_group_message_reaction")]


class GroupMessageReadReceipt(models.Model):
    message = models.ForeignKey(GroupMessage, on_delete=models.CASCADE, related_name="read_receipts")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_message_read_receipts")
    read_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["message", "user"], name="unique_group_message_read_receipt")]


class GroupMessageDeliveryReceipt(models.Model):
    message = models.ForeignKey(GroupMessage, on_delete=models.CASCADE, related_name="delivery_receipts")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_message_delivery_receipts")
    delivered_at = models.DateTimeField(auto_now_add=True)
    device_id = models.CharField(max_length=120, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["message", "user", "device_id"], name="unique_group_message_delivery")]


class GroupMessageDeletion(models.Model):
    message = models.ForeignKey(GroupMessage, on_delete=models.CASCADE, related_name="deleted_for")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_message_deletions")
    deleted_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["message", "user"], name="unique_group_message_delete")]


class GroupMessageStar(models.Model):
    message = models.ForeignKey(GroupMessage, on_delete=models.CASCADE, related_name="stars")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_message_stars")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["message", "user"], name="unique_group_message_star")]


class GroupMessagePin(models.Model):
    message = models.ForeignKey(GroupMessage, on_delete=models.CASCADE, related_name="pins")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="message_pins")
    pinned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_message_pins")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["message", "group"], name="unique_group_message_pin")]


class GroupMute(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="mute_records")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_mutes")
    muted_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["group", "user"], name="unique_group_mute")]


class GroupArchive(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="archive_records")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_archives")
    archived_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["group", "user"], name="unique_group_archive")]


class GroupClearState(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="clear_states")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_clear_states")
    cleared_before = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["group", "user"], name="unique_group_clear_state")]


class GroupReport(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_reports")
    reason = models.CharField(max_length=40, choices=PostReport.REASONS)
    details = models.TextField(blank=True, max_length=1000)
    status = models.CharField(max_length=20, choices=MessageReport.STATUSES, default=MessageReport.STATUS_PENDING)
    context_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["group", "reporter", "reason"], name="unique_group_report_reason")]


class GroupMessageReport(models.Model):
    message = models.ForeignKey(GroupMessage, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_message_reports")
    reason = models.CharField(max_length=40, choices=PostReport.REASONS)
    details = models.TextField(blank=True, max_length=1000)
    status = models.CharField(max_length=20, choices=MessageReport.STATUSES, default=MessageReport.STATUS_PENDING)
    context_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["message", "reporter", "reason"], name="unique_group_message_report_reason")]


class GroupAuditLog(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="audit_logs")
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="group_audit_logs")
    action = models.CharField(max_length=120)
    target = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=["group", "created_at"]), models.Index(fields=["action"])]


class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notification_preferences")
    private_messages = models.BooleanField(default=True)
    message_requests = models.BooleanField(default=True)
    group_messages = models.BooleanField(default=True)
    group_mentions = models.BooleanField(default=True)
    group_role_changes = models.BooleanField(default=True)
    incoming_calls = models.BooleanField(default=True)
    missed_calls = models.BooleanField(default=True)
    declined_calls = models.BooleanField(default=True)
    group_calls = models.BooleanField(default=True)
    followers = models.BooleanField(default=True)
    likes = models.BooleanField(default=True)
    comments = models.BooleanField(default=True)
    story_reactions = models.BooleanField(default=True)
    reel_activity = models.BooleanField(default=True)
    security_alerts = models.BooleanField(default=True)
    marketing = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)
    notification_previews = models.BooleanField(default=True)
    sound = models.BooleanField(default=True)
    vibration = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)


class NotificationDelivery(models.Model):
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="delivery_records")
    channel = models.CharField(max_length=20, default="in_app")
    status = models.CharField(max_length=20, default="pending")
    provider_message = models.CharField(max_length=255, blank=True)
    attempted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class PushNotificationDelivery(models.Model):
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="push_deliveries")
    device = models.ForeignKey(UserDevice, on_delete=models.SET_NULL, null=True, blank=True, related_name="push_deliveries")
    status = models.CharField(max_length=30, default="not_configured")
    provider = models.CharField(max_length=40, default="expo")
    provider_response = models.JSONField(default=dict, blank=True)
    deep_link = models.CharField(max_length=255, blank=True)
    attempted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class NotificationBatch(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notification_batches")
    grouping_key = models.CharField(max_length=120)
    notification_type = models.CharField(max_length=60)
    count = models.PositiveIntegerField(default=1)
    latest_notification = models.ForeignKey(Notification, on_delete=models.SET_NULL, null=True, blank=True, related_name="latest_for_batches")
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["recipient", "grouping_key"], name="unique_notification_batch")]


class AdminAnnouncement(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_SCHEDULED = "scheduled"
    STATUS_SENT = "sent"
    STATUS_CANCELED = "canceled"
    title = models.CharField(max_length=120)
    body = models.TextField(max_length=1000)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="admin_announcements")
    target = models.CharField(max_length=40, default="all")
    payload = models.JSONField(default=dict, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default=STATUS_DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



# Phase 7 calls, moderation, appeals, and professional accounts
class Call(models.Model):
    TYPE_PRIVATE_VOICE = "private_voice"
    TYPE_PRIVATE_VIDEO = "private_video"
    TYPE_GROUP_VOICE = "group_voice"
    TYPE_GROUP_VIDEO = "group_video"
    TYPES = [(TYPE_PRIVATE_VOICE, "Private voice"), (TYPE_PRIVATE_VIDEO, "Private video"), (TYPE_GROUP_VOICE, "Group voice"), (TYPE_GROUP_VIDEO, "Group video")]
    STATUS_INITIATING = "initiating"
    STATUS_RINGING = "ringing"
    STATUS_CONNECTING = "connecting"
    STATUS_ACTIVE = "active"
    STATUS_RECONNECTING = "reconnecting"
    STATUS_DECLINED = "declined"
    STATUS_MISSED = "missed"
    STATUS_BUSY = "busy"
    STATUS_FAILED = "failed"
    STATUS_ENDED = "ended"
    STATUS_CANCELLED = "cancelled"
    STATUSES = [(STATUS_INITIATING, "Initiating"), (STATUS_RINGING, "Ringing"), (STATUS_CONNECTING, "Connecting"), (STATUS_ACTIVE, "Active"), (STATUS_RECONNECTING, "Reconnecting"), (STATUS_DECLINED, "Declined"), (STATUS_MISSED, "Missed"), (STATUS_BUSY, "Busy"), (STATUS_FAILED, "Failed"), (STATUS_ENDED, "Ended"), (STATUS_CANCELLED, "Cancelled")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call_type = models.CharField(max_length=30, choices=TYPES)
    conversation = models.ForeignKey(Conversation, on_delete=models.SET_NULL, null=True, blank=True, related_name="calls")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name="calls")
    initiator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="initiated_calls")
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_INITIATING)
    started_at = models.DateTimeField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    failure_reason = models.CharField(max_length=280, blank=True)
    provider = models.CharField(max_length=40, default="webrtc")
    signaling_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        indexes = [models.Index(fields=["status", "updated_at"]), models.Index(fields=["initiator", "created_at"]), models.Index(fields=["conversation", "created_at"]), models.Index(fields=["group", "created_at"])]


class CallParticipant(models.Model):
    ROLE_HOST = "host"
    ROLE_INVITEE = "invitee"
    ROLE_MEMBER = "member"
    ROLES = [(ROLE_HOST, "Host"), (ROLE_INVITEE, "Invitee"), (ROLE_MEMBER, "Member")]
    STATUS_INVITED = "invited"
    STATUS_RINGING = "ringing"
    STATUS_JOINED = "joined"
    STATUS_LEFT = "left"
    STATUS_DECLINED = "declined"
    STATUS_MISSED = "missed"
    STATUS_BUSY = "busy"
    STATUS_REMOVED = "removed"
    STATUSES = [(STATUS_INVITED, "Invited"), (STATUS_RINGING, "Ringing"), (STATUS_JOINED, "Joined"), (STATUS_LEFT, "Left"), (STATUS_DECLINED, "Declined"), (STATUS_MISSED, "Missed"), (STATUS_BUSY, "Busy"), (STATUS_REMOVED, "Removed")]
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="call_participations")
    role = models.CharField(max_length=20, choices=ROLES, default=ROLE_INVITEE)
    join_status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_INVITED)
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    device_identifier = models.CharField(max_length=120, blank=True)
    is_muted = models.BooleanField(default=False)
    camera_enabled = models.BooleanField(default=False)
    screen_share_enabled = models.BooleanField(default=False)
    connection_quality = models.JSONField(default=dict, blank=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["call", "user"], name="unique_call_participant")]
        indexes = [models.Index(fields=["call", "join_status"]), models.Index(fields=["user", "updated_at"])]


class CallDeviceSession(models.Model):
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name="device_sessions")
    participant = models.ForeignKey(CallParticipant, on_delete=models.CASCADE, related_name="device_sessions")
    device_id = models.CharField(max_length=120)
    channel_name = models.CharField(max_length=255, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["call", "participant", "device_id"], name="unique_call_device_session")]


class CallSignalEvent(models.Model):
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name="signal_events")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_call_signal_events")
    event_name = models.CharField(max_length=60)
    request_id = models.CharField(max_length=120, blank=True)
    safe_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=["call", "created_at"]), models.Index(fields=["event_name"])]


class CallHistory(models.Model):
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name="history_items")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="call_history")
    direction = models.CharField(max_length=20)
    local_deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["call", "user"], name="unique_call_history_user")]
        indexes = [models.Index(fields=["user", "created_at"])]


class CallReport(models.Model):
    REASONS = PostReport.REASONS + [("impersonation", "Impersonation"), ("sexual_misconduct", "Sexual misconduct"), ("threats", "Threats")]
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="call_reports")
    reason = models.CharField(max_length=40, choices=REASONS)
    details = models.TextField(blank=True, max_length=1000)
    status = models.CharField(max_length=20, choices=MessageReport.STATUSES, default=MessageReport.STATUS_PENDING)
    context_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["call", "reporter", "reason"], name="unique_call_report_reason")]
        indexes = [models.Index(fields=["status", "created_at"])]


class ModerationAction(models.Model):
    STATUS_PENDING = "pending"
    STATUS_UNDER_REVIEW = "under_review"
    STATUS_ESCALATED = "escalated"
    STATUS_RESOLVED = "resolved"
    STATUS_REJECTED = "rejected"
    STATUS_ACTION_TAKEN = "action_taken"
    STATUSES = [(STATUS_PENDING, "Pending"), (STATUS_UNDER_REVIEW, "Under review"), (STATUS_ESCALATED, "Escalated"), (STATUS_RESOLVED, "Resolved"), (STATUS_REJECTED, "Rejected"), (STATUS_ACTION_TAKEN, "Action taken")]
    ACTION_WARNING = "warning"
    ACTION_CONTENT_REMOVAL = "content_removal"
    ACTION_FEATURE_RESTRICTION = "feature_restriction"
    ACTION_CALL_RESTRICTION = "call_restriction"
    ACTION_GROUP_RESTRICTION = "group_restriction"
    ACTION_TEMP_SUSPENSION = "temporary_suspension"
    ACTION_PERMANENT_BAN = "permanent_ban"
    ACTION_VERIFICATION_REMOVAL = "verification_removal"
    ACTION_CREATOR_REMOVAL = "creator_status_removal"
    ACTION_BUSINESS_REMOVAL = "business_status_removal"
    ACTIONS = [(ACTION_WARNING, "Warning"), (ACTION_CONTENT_REMOVAL, "Content removal"), (ACTION_FEATURE_RESTRICTION, "Feature restriction"), (ACTION_CALL_RESTRICTION, "Call restriction"), (ACTION_GROUP_RESTRICTION, "Group restriction"), (ACTION_TEMP_SUSPENSION, "Temporary suspension"), (ACTION_PERMANENT_BAN, "Permanent ban"), (ACTION_VERIFICATION_REMOVAL, "Verification removal"), (ACTION_CREATOR_REMOVAL, "Creator status removal"), (ACTION_BUSINESS_REMOVAL, "Business status removal")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="moderation_actions")
    moderator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="issued_moderation_actions")
    action_type = models.CharField(max_length=40, choices=ACTIONS)
    status = models.CharField(max_length=30, choices=STATUSES, default=STATUS_PENDING)
    reason = models.CharField(max_length=280)
    object_type = models.CharField(max_length=60, blank=True)
    object_id = models.CharField(max_length=80, blank=True)
    internal_notes = models.TextField(blank=True)
    appeal_eligible = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        indexes = [models.Index(fields=["target_user", "status"]), models.Index(fields=["status", "created_at"]), models.Index(fields=["object_type", "object_id"])]


class CallModerationAction(models.Model):
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name="moderation_actions")
    moderation_action = models.ForeignKey(ModerationAction, on_delete=models.CASCADE, related_name="call_actions")
    created_at = models.DateTimeField(auto_now_add=True)


class UserFeatureRestriction(models.Model):
    FEATURE_POST = "post"
    FEATURE_COMMENT = "comment"
    FEATURE_STORY = "story"
    FEATURE_REEL = "reel"
    FEATURE_MESSAGE = "message"
    FEATURE_CREATE_GROUP = "create_group"
    FEATURE_JOIN_GROUP = "join_group"
    FEATURE_START_CALL = "start_call"
    FEATURE_RECEIVE_CALL = "receive_call"
    FEATURE_PROFESSIONAL = "professional"
    FEATURES = [(FEATURE_POST, "Post"), (FEATURE_COMMENT, "Comment"), (FEATURE_STORY, "Story"), (FEATURE_REEL, "Reel"), (FEATURE_MESSAGE, "Message"), (FEATURE_CREATE_GROUP, "Create group"), (FEATURE_JOIN_GROUP, "Join group"), (FEATURE_START_CALL, "Start call"), (FEATURE_RECEIVE_CALL, "Receive call"), (FEATURE_PROFESSIONAL, "Professional features")]
    STATUS_ACTIVE = "active"
    STATUS_EXPIRED = "expired"
    STATUS_REVOKED = "revoked"
    STATUSES = [(STATUS_ACTIVE, "Active"), (STATUS_EXPIRED, "Expired"), (STATUS_REVOKED, "Revoked")]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="feature_restrictions")
    feature = models.CharField(max_length=40, choices=FEATURES)
    reason = models.CharField(max_length=280)
    moderator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="issued_feature_restrictions")
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_ACTIVE)
    appeal_eligible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        indexes = [models.Index(fields=["user", "feature", "status"]), models.Index(fields=["expires_at"])]


class ModerationAppeal(models.Model):
    STATUS_SUBMITTED = "submitted"
    STATUS_UNDER_REVIEW = "under_review"
    STATUS_APPROVED = "approved"
    STATUS_PARTIALLY_APPROVED = "partially_approved"
    STATUS_REJECTED = "rejected"
    ACTIVE_STATUSES = [STATUS_SUBMITTED, STATUS_UNDER_REVIEW]
    STATUSES = [(STATUS_SUBMITTED, "Submitted"), (STATUS_UNDER_REVIEW, "Under review"), (STATUS_APPROVED, "Approved"), (STATUS_PARTIALLY_APPROVED, "Partially approved"), (STATUS_REJECTED, "Rejected")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.ForeignKey(ModerationAction, on_delete=models.CASCADE, related_name="appeals")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="moderation_appeals")
    explanation = models.TextField(max_length=2000)
    status = models.CharField(max_length=30, choices=STATUSES, default=STATUS_SUBMITTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        indexes = [models.Index(fields=["user", "status", "created_at"]), models.Index(fields=["action", "status"])]


class AppealAttachment(models.Model):
    appeal = models.ForeignKey(ModerationAppeal, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="appeals/", null=True, blank=True)
    file_name = models.CharField(max_length=180)
    mime_type = models.CharField(max_length=120)
    file_size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class AppealDecision(models.Model):
    appeal = models.OneToOneField(ModerationAppeal, on_delete=models.CASCADE, related_name="decision")
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="appeal_decisions")
    decision = models.CharField(max_length=30, choices=ModerationAppeal.STATUSES)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ModerationEvidenceAccess(models.Model):
    moderator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="moderation_evidence_accesses")
    object_type = models.CharField(max_length=60)
    object_id = models.CharField(max_length=80)
    reason = models.CharField(max_length=280, blank=True)
    accessed_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=["moderator", "accessed_at"]), models.Index(fields=["object_type", "object_id"])]


class ProfessionalAccount(models.Model):
    TYPE_CREATOR = "creator"
    TYPE_BUSINESS = "business"
    TYPES = [(TYPE_CREATOR, "Creator"), (TYPE_BUSINESS, "Business")]
    STATUS_ACTIVE = "active"
    STATUS_PENDING = "pending"
    STATUS_SUSPENDED = "suspended"
    STATUS_REMOVED = "removed"
    STATUSES = [(STATUS_ACTIVE, "Active"), (STATUS_PENDING, "Pending"), (STATUS_SUSPENDED, "Suspended"), (STATUS_REMOVED, "Removed")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="professional_account")
    account_type = models.CharField(max_length=20, choices=TYPES)
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_ACTIVE)
    category = models.CharField(max_length=80)
    public_contact_enabled = models.BooleanField(default=False)
    dashboard_settings = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class CreatorProfile(models.Model):
    professional_account = models.OneToOneField(ProfessionalAccount, on_delete=models.CASCADE, related_name="creator_profile")
    creator_category = models.CharField(max_length=80)
    professional_bio = models.CharField(max_length=280, blank=True)
    collaboration_email = models.EmailField(blank=True)
    public_contact = models.CharField(max_length=120, blank=True)
    collaboration_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class BusinessProfile(models.Model):
    professional_account = models.OneToOneField(ProfessionalAccount, on_delete=models.CASCADE, related_name="business_profile")
    business_name = models.CharField(max_length=120)
    business_category = models.CharField(max_length=80)
    description = models.TextField(blank=True, max_length=1000)
    website = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    show_phone_number = models.BooleanField(default=False)
    public_phone_number = models.CharField(max_length=20, blank=True)
    physical_location = models.CharField(max_length=180, blank=True)
    business_hours = models.JSONField(default=dict, blank=True)
    contact_buttons = models.JSONField(default=list, blank=True)
    team_architecture = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class VerificationRequest(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_UNDER_REVIEW = "under_review"
    STATUS_MORE_INFO = "more_information_required"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CANCELLED = "cancelled"
    STATUSES = [(STATUS_DRAFT, "Draft"), (STATUS_SUBMITTED, "Submitted"), (STATUS_UNDER_REVIEW, "Under review"), (STATUS_MORE_INFO, "More information required"), (STATUS_APPROVED, "Approved"), (STATUS_REJECTED, "Rejected"), (STATUS_CANCELLED, "Cancelled")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_requests")
    account_type = models.CharField(max_length=20, choices=ProfessionalAccount.TYPES)
    public_name = models.CharField(max_length=120)
    category = models.CharField(max_length=80)
    reason = models.TextField(max_length=2000)
    supporting_links = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=40, choices=STATUSES, default=STATUS_SUBMITTED)
    internal_notes = models.TextField(blank=True)
    decided_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="decided_verification_requests")
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        indexes = [models.Index(fields=["user", "status", "created_at"]), models.Index(fields=["status", "created_at"])]


class VerificationDocument(models.Model):
    request = models.ForeignKey(VerificationRequest, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to="verification-documents/", null=True, blank=True)
    file_name = models.CharField(max_length=180)
    mime_type = models.CharField(max_length=120)
    file_size = models.PositiveIntegerField(default=0)
    retention_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ProfessionalInsightDaily(models.Model):
    professional_account = models.ForeignKey(ProfessionalAccount, on_delete=models.CASCADE, related_name="daily_insights")
    date = models.DateField()
    profile_views = models.PositiveIntegerField(default=0)
    follower_growth = models.IntegerField(default=0)
    post_impressions = models.PositiveIntegerField(default=0)
    post_reach = models.PositiveIntegerField(default=0)
    post_engagement = models.PositiveIntegerField(default=0)
    reel_views = models.PositiveIntegerField(default=0)
    reel_watch_time_seconds = models.PositiveIntegerField(default=0)
    story_views = models.PositiveIntegerField(default=0)
    story_completion = models.FloatField(default=0)
    saves = models.PositiveIntegerField(default=0)
    shares = models.PositiveIntegerField(default=0)
    comments = models.PositiveIntegerField(default=0)
    message_response_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["professional_account", "date"], name="unique_professional_insight_day")]


class ContentInsight(models.Model):
    professional_account = models.ForeignKey(ProfessionalAccount, on_delete=models.CASCADE, related_name="content_insights")
    content_type = models.CharField(max_length=30)
    object_id = models.CharField(max_length=80)
    impressions = models.PositiveIntegerField(default=0)
    reach = models.PositiveIntegerField(default=0)
    engagement = models.PositiveIntegerField(default=0)
    saves = models.PositiveIntegerField(default=0)
    shares = models.PositiveIntegerField(default=0)
    comments = models.PositiveIntegerField(default=0)
    watch_time_seconds = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["professional_account", "content_type", "object_id"], name="unique_content_insight_object")]


class AudienceInsight(models.Model):
    professional_account = models.ForeignKey(ProfessionalAccount, on_delete=models.CASCADE, related_name="audience_insights")
    snapshot_date = models.DateField()
    metrics = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["professional_account", "snapshot_date"], name="unique_audience_insight_snapshot")]


class BusinessContactAction(models.Model):
    professional_account = models.ForeignKey(ProfessionalAccount, on_delete=models.CASCADE, related_name="contact_actions")
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="business_contact_actions")
    action_type = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=["professional_account", "created_at"])]



# Phase 8 production readiness: data rights and operations
class DataExportRequest(models.Model):
    STATUS_REQUESTED = "requested"
    STATUS_PROCESSING = "processing"
    STATUS_READY = "ready"
    STATUS_FAILED = "failed"
    STATUS_EXPIRED = "expired"
    STATUSES = [(STATUS_REQUESTED, "Requested"), (STATUS_PROCESSING, "Processing"), (STATUS_READY, "Ready"), (STATUS_FAILED, "Failed"), (STATUS_EXPIRED, "Expired")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="data_export_requests")
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_REQUESTED)
    export_scope = models.JSONField(default=list, blank=True)
    file = models.FileField(upload_to="data-exports/", null=True, blank=True)
    download_token_hash = models.CharField(max_length=128, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=280, blank=True)
    recent_auth_confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        indexes = [models.Index(fields=["user", "status", "created_at"]), models.Index(fields=["expires_at"])]


class AccountDeletionRequest(models.Model):
    STATUS_REQUESTED = "requested"
    STATUS_CANCELLED = "cancelled"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUSES = [(STATUS_REQUESTED, "Requested"), (STATUS_CANCELLED, "Cancelled"), (STATUS_PROCESSING, "Processing"), (STATUS_COMPLETED, "Completed")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="account_deletion_requests")
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_REQUESTED)
    reason = models.CharField(max_length=280, blank=True)
    grace_period_ends_at = models.DateTimeField()
    cancelled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    retention_notes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        indexes = [models.Index(fields=["user", "status", "created_at"]), models.Index(fields=["grace_period_ends_at"])]


class OperationalEvent(models.Model):
    LEVEL_INFO = "info"
    LEVEL_WARNING = "warning"
    LEVEL_ERROR = "error"
    LEVELS = [(LEVEL_INFO, "Info"), (LEVEL_WARNING, "Warning"), (LEVEL_ERROR, "Error")]
    event_type = models.CharField(max_length=80)
    level = models.CharField(max_length=20, choices=LEVELS, default=LEVEL_INFO)
    correlation_id = models.CharField(max_length=80, blank=True)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="operational_events")
    safe_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=["event_type", "created_at"]), models.Index(fields=["level", "created_at"]), models.Index(fields=["correlation_id"])]
