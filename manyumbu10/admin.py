from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import AdminAuditLog, BlockedUser, CloseFriend, Comment, CommentLike, EmailVerificationCode, Follow, FollowRequest, GoogleAccount, Hashtag, HiddenPost, MutedUser, Notification, PasswordResetCode, Post, PostAudienceUser, PostHashtag, PostLike, PostMedia, PostMention, PostReport, PostTag, RestrictedUser, SavedPost, User, UserPrivacySettings, UserProfile, UserSession


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    ordering = ("phone_number",)
    list_display = ("phone_number", "username", "email", "is_email_verified", "is_active", "is_staff")
    search_fields = ("phone_number", "username", "email", "full_name")
    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Personal info", {"fields": ("email", "username", "full_name", "date_of_birth", "profile_picture")}),
        ("Verification", {"fields": ("is_email_verified", "email_verified_at", "is_verified")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Roles", {"fields": ("is_creator", "is_business")}),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone_number", "email", "username", "full_name", "date_of_birth", "password1", "password2", "is_active", "is_email_verified"),
        }),
    )
    readonly_fields = ("created_at", "updated_at")


admin.site.register(UserProfile)
admin.site.register(UserSession)
admin.site.register(EmailVerificationCode)
admin.site.register(PasswordResetCode)
admin.site.register(GoogleAccount)

admin.site.register(UserPrivacySettings)
admin.site.register(Follow)
admin.site.register(FollowRequest)
admin.site.register(BlockedUser)
admin.site.register(RestrictedUser)
admin.site.register(MutedUser)
admin.site.register(CloseFriend)


admin.site.register(Post)
admin.site.register(PostMedia)
admin.site.register(PostLike)
admin.site.register(SavedPost)
admin.site.register(HiddenPost)
admin.site.register(PostTag)
admin.site.register(PostMention)
admin.site.register(PostAudienceUser)
admin.site.register(Hashtag)
admin.site.register(PostHashtag)
admin.site.register(Comment)
admin.site.register(CommentLike)
admin.site.register(Notification)
admin.site.register(PostReport)
admin.site.register(AdminAuditLog)

