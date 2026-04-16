from __future__ import annotations

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class EnrollmentStatus(models.TextChoices):
    ENROLLED = "enrolled", "Enrolled"
    CANCELED = "canceled", "Canceled"


class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    language = models.CharField(max_length=64)
    location = models.CharField(max_length=255)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    capacity = models.PositiveIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")),
                name="event_ends_after_starts",
            ),
            models.CheckConstraint(
                condition=Q(capacity__isnull=True) | Q(capacity__gte=1),
                name="event_capacity_null_or_at_least_one",
            ),
        ]
        indexes = [
            models.Index(fields=["starts_at"]),
            models.Index(fields=["language"]),
            models.Index(fields=["location"]),
            models.Index(fields=["created_by", "starts_at"]),
        ]

    def __str__(self) -> str:
        return f"Event({self.pk}, {self.title!r})"

    def clean(self) -> None:
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "ends_at must be after starts_at."})
        if self.capacity is not None and self.capacity < 1:
            raise ValidationError(
                {"capacity": "capacity must be at least 1 when set."},
            )


class Enrollment(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    seeker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="event_enrollments",
    )
    status = models.CharField(max_length=32, choices=EnrollmentStatus.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "seeker"],
                condition=Q(status=EnrollmentStatus.ENROLLED),
                name="enrollment_one_active_per_event_seeker",
            ),
        ]
        indexes = [
            models.Index(fields=["event", "status"]),
            models.Index(fields=["seeker", "status"]),
        ]

    def __str__(self) -> str:
        return f"Enrollment({self.pk}, event={self.event_id}, {self.status})"
