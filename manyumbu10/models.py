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
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications_created")
    notification_type = models.CharField(max_length=40)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    message = models.CharField(max_length=180, blank=True)
    is_read = models.BooleanField(default=False)
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
