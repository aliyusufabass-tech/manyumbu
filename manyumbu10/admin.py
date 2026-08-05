from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import EmailVerificationCode, GoogleAccount, PasswordResetCode, User, UserProfile, UserSession


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
