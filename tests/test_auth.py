from __future__ import annotations

import re
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import EmailOTP


@pytest.fixture
def api_client():
    return APIClient()


def _envelope(response):
    return response.json()


def assert_error_envelope(response):
    assert response.status_code in (400, 401, 403, 404, 405, 409, 429)
    body = _envelope(response)
    assert "detail" in body
    assert "code" in body


def _otp_from_last_email() -> str:
    assert len(mail.outbox) >= 1
    match = re.search(r"\b(\d{6})\b", mail.outbox[-1].body)
    assert match is not None
    return match.group(1)


@pytest.mark.django_db
def test_signup_accepts_only_email_password_role(api_client):
    response = api_client.post(
        "/api/auth/signup/",
        {"email": "user@example.com", "password": "StrongPass9!", "role": "seeker"},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"
    assert response.json()["role"] == "seeker"


@pytest.mark.django_db
def test_signup_rejects_username_in_payload(api_client):
    response = api_client.post(
        "/api/auth/signup/",
        {
            "email": "user2@example.com",
            "password": "StrongPass9!",
            "role": "seeker",
            "username": "nope",
        },
        format="json",
    )
    assert response.status_code == 400
    assert_error_envelope(response)
    assert "username" in str(_envelope(response)["detail"])


@pytest.mark.django_db
def test_duplicate_email_signup_rejected_cleanly(api_client):
    payload = {"email": "dup@example.com", "password": "StrongPass9!", "role": "seeker"}
    assert api_client.post("/api/auth/signup/", payload, format="json").status_code == 201
    response = api_client.post("/api/auth/signup/", payload, format="json")
    assert response.status_code == 400
    assert_error_envelope(response)
    assert "email" in str(_envelope(response)["detail"]).lower()


@pytest.mark.django_db
def test_verify_email_success_with_valid_otp(api_client):
    api_client.post(
        "/api/auth/signup/",
        {"email": "verify@example.com", "password": "StrongPass9!", "role": "facilitator"},
        format="json",
    )
    otp = _otp_from_last_email()
    response = api_client.post(
        "/api/auth/verify-email/",
        {"email": "verify@example.com", "otp": otp},
        format="json",
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_verify_email_fails_for_wrong_otp(api_client):
    api_client.post(
        "/api/auth/signup/",
        {"email": "wrong@example.com", "password": "StrongPass9!", "role": "seeker"},
        format="json",
    )
    response = api_client.post(
        "/api/auth/verify-email/",
        {"email": "wrong@example.com", "otp": "000000"},
        format="json",
    )
    assert response.status_code == 400
    assert_error_envelope(response)


@pytest.mark.django_db
def test_verify_email_fails_for_expired_otp(api_client):
    api_client.post(
        "/api/auth/signup/",
        {"email": "expired@example.com", "password": "StrongPass9!", "role": "seeker"},
        format="json",
    )
    otp = _otp_from_last_email()
    user = User.objects.get(email="expired@example.com")
    EmailOTP.objects.filter(user=user).update(
        expires_at=timezone.now() - timedelta(minutes=10)
    )
    response = api_client.post(
        "/api/auth/verify-email/",
        {"email": "expired@example.com", "otp": otp},
        format="json",
    )
    assert response.status_code == 400
    assert_error_envelope(response)


@pytest.mark.django_db
def test_verify_email_fails_after_attempts_exhausted(api_client):
    api_client.post(
        "/api/auth/signup/",
        {"email": "attempts@example.com", "password": "StrongPass9!", "role": "seeker"},
        format="json",
    )
    for _ in range(int(settings.OTP_MAX_ATTEMPTS)):
        response = api_client.post(
            "/api/auth/verify-email/",
            {"email": "attempts@example.com", "otp": "000000"},
            format="json",
        )
        assert response.status_code == 400
        assert_error_envelope(response)

    exhausted = api_client.post(
        "/api/auth/verify-email/",
        {"email": "attempts@example.com", "otp": "000000"},
        format="json",
    )
    assert exhausted.status_code == 400
    assert_error_envelope(exhausted)
    assert "attempt" in str(_envelope(exhausted)["detail"]).lower()


@pytest.mark.django_db
def test_unverified_user_cannot_log_in(api_client):
    api_client.post(
        "/api/auth/signup/",
        {"email": "unverified@example.com", "password": "StrongPass9!", "role": "seeker"},
        format="json",
    )
    response = api_client.post(
        "/api/auth/login/",
        {"email": "unverified@example.com", "password": "StrongPass9!"},
        format="json",
    )
    assert response.status_code == 401
    assert_error_envelope(response)
    assert "verified" in str(_envelope(response)["detail"]).lower()


@pytest.mark.django_db
def test_verified_user_can_log_in_with_email_and_password(api_client):
    api_client.post(
        "/api/auth/signup/",
        {"email": "login@example.com", "password": "StrongPass9!", "role": "seeker"},
        format="json",
    )
    otp = _otp_from_last_email()
    assert (
        api_client.post(
            "/api/auth/verify-email/",
            {"email": "login@example.com", "otp": otp},
            format="json",
        ).status_code
        == 200
    )

    response = api_client.post(
        "/api/auth/login/",
        {"email": "login@example.com", "password": "StrongPass9!"},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert "access" in body
    assert "refresh" in body


@pytest.mark.django_db
def test_login_rejects_username_field(api_client):
    response = api_client.post(
        "/api/auth/login/",
        {"email": "login@example.com", "password": "StrongPass9!", "username": "x"},
        format="json",
    )
    assert response.status_code == 400
    assert_error_envelope(response)


@pytest.mark.django_db
def test_refresh_endpoint_works(api_client):
    api_client.post(
        "/api/auth/signup/",
        {"email": "refresh@example.com", "password": "StrongPass9!", "role": "seeker"},
        format="json",
    )
    otp = _otp_from_last_email()
    assert (
        api_client.post(
            "/api/auth/verify-email/",
            {"email": "refresh@example.com", "otp": otp},
            format="json",
        ).status_code
        == 200
    )
    login = api_client.post(
        "/api/auth/login/",
        {"email": "refresh@example.com", "password": "StrongPass9!"},
        format="json",
    )
    refresh = login.json()["refresh"]

    refreshed = api_client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
    assert refreshed.status_code == 200
    assert "access" in refreshed.json()


@pytest.mark.django_db
def test_validation_error_preserves_envelope(api_client):
    response = api_client.post("/api/auth/signup/", {"email": "not-an-email"}, format="json")
    assert response.status_code == 400
    body = _envelope(response)
    assert "detail" in body
    assert "code" in body
    assert body["code"] == "validation_error"
