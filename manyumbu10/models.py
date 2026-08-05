from datetime import timedelta

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
