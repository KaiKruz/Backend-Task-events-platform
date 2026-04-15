from __future__ import annotations

from django.urls import path

from accounts.views import LoginView, RefreshView, SignupView, VerifyEmailView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="auth-signup"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
]
