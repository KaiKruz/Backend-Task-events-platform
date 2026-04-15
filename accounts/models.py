from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models


class AccountRole(models.TextChoices):
    SEEKER = "seeker", "Seeker"
    FACILITATOR = "facilitator", "Facilitator"


class AccountProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="account_profile",
    )
    role = models.CharField(max_length=32, choices=AccountRole.choices)
    email_verified = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"AccountProfile({self.user_id}, {self.role})"


class EmailOTP(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_otps",
    )
    code_hash = models.CharField(max_length=256)
    expires_at = models.DateTimeField()
    attempts_left = models.PositiveSmallIntegerField()
    is_used = models.BooleanField(default=False)
    last_sent_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["user", "-last_sent_at"]),
        ]

    def __str__(self) -> str:
        return f"EmailOTP(user={self.user_id}, used={self.is_used})"
