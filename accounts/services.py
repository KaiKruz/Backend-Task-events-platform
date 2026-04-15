from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import AccountProfile, AccountRole, EmailOTP


def normalize_email(email: str) -> str:
    return email.strip().lower()


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _invalidate_open_otps(user: User) -> None:
    EmailOTP.objects.filter(user=user, is_used=False).update(is_used=True)


def _create_otp_and_send(user: User) -> None:
    plain = generate_otp_code()
    expires_at = timezone.now() + timedelta(minutes=int(settings.OTP_EXPIRY_MINUTES))
    _invalidate_open_otps(user)
    EmailOTP.objects.create(
        user=user,
        code_hash=make_password(plain),
        expires_at=expires_at,
        attempts_left=int(settings.OTP_MAX_ATTEMPTS),
        is_used=False,
        last_sent_at=timezone.now(),
    )
    send_mail(
        subject="Verify your email",
        message=f"Your verification code is: {plain}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


@transaction.atomic
def signup(*, email: str, password: str, role: str) -> User:
    normalized = normalize_email(email)
    if role not in AccountRole.values:
        raise ValidationError({"role": "Invalid role."})
    try:
        user = User.objects.create_user(
            username=normalized,
            email=normalized,
            password=password,
        )
    except IntegrityError as exc:
        raise ValidationError(
            {"email": "An account with this email already exists."}
        ) from exc

    AccountProfile.objects.create(
        user=user,
        role=role,
        email_verified=False,
    )
    _create_otp_and_send(user)
    return user


def verify_email(*, email: str, otp: str) -> None:
    normalized = normalize_email(email)
    user = (
        User.objects.filter(email__iexact=normalized).select_related("account_profile").first()
    )
    if user is None:
        raise ValidationError({"email": "Invalid email or verification code."})

    otp_row = (
        EmailOTP.objects.filter(user=user, is_used=False)
        .order_by("-last_sent_at", "-id")
        .first()
    )
    if otp_row is None:
        raise ValidationError({"otp": "No active verification code found."})

    now = timezone.now()
    if now > otp_row.expires_at:
        raise ValidationError({"otp": "Verification code has expired."})

    if not check_password(otp, otp_row.code_hash):
        with transaction.atomic():
            locked = EmailOTP.objects.select_for_update().get(pk=otp_row.pk)
            locked.attempts_left = max(0, int(locked.attempts_left) - 1)
            locked.save(update_fields=["attempts_left"])
            attempts_left = locked.attempts_left
        if attempts_left <= 0:
            raise ValidationError({"otp": "Too many failed attempts. Request a new code."})
        raise ValidationError({"otp": "Invalid verification code."})

    with transaction.atomic():
        locked_otp = EmailOTP.objects.select_for_update().get(pk=otp_row.pk)
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if locked_otp.is_used:
            raise ValidationError({"otp": "No active verification code found."})
        if timezone.now() > locked_otp.expires_at:
            raise ValidationError({"otp": "Verification code has expired."})
        locked_otp.is_used = True
        locked_otp.save(update_fields=["is_used"])
        profile = locked_user.account_profile
        if not profile.email_verified:
            profile.email_verified = True
            profile.save(update_fields=["email_verified"])
