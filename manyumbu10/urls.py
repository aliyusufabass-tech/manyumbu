from django.urls import path

from .views import (
    ForgotPasswordView,
    GoogleAuthStartView,
    LoginView,
    RegisterView,
    ResendVerificationView,
    ResetPasswordView,
    TokenRefreshView,
    VerifyEmailView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("auth/resend-code/", ResendVerificationView.as_view(), name="auth-resend-code"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("auth/forgot-password/", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("auth/reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"),
    path("auth/google/start/", GoogleAuthStartView.as_view(), name="auth-google-start"),
]
