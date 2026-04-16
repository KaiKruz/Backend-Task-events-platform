from __future__ import annotations

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count
from rest_framework.exceptions import ValidationError

from accounts.models import AccountProfile, AccountRole

from .models import Enrollment, EnrollmentStatus, Event


def _require_facilitator(user: User) -> AccountProfile:
    profile = AccountProfile.objects.filter(user=user).first()
    if (
        profile is None
        or profile.role != AccountRole.FACILITATOR
        or not profile.email_verified
    ):
        raise ValidationError({"created_by": "Only facilitators may create events."})
    return profile


def _require_seeker(user: User) -> AccountProfile:
    profile = AccountProfile.objects.filter(user=user).first()
    if profile is None or profile.role != AccountRole.SEEKER:
        raise ValidationError({"seeker": "Only seekers may enroll in events."})
    return profile


def create_event(
    *,
    title: str,
    description: str,
    language: str,
    location: str,
    starts_at,
    ends_at,
    capacity: int | None,
    created_by: User,
) -> Event:
    """Create an event; facilitator-only (enforced in services, not via FK)."""
    _require_facilitator(created_by)
    event = Event(
        title=title,
        description=description,
        language=language,
        location=location,
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=capacity,
        created_by=created_by,
    )
    try:
        event.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict or exc.messages) from exc
    event.save()
    return event


def update_event(*, event: Event, **fields) -> Event:
    for field_name, value in fields.items():
        setattr(event, field_name, value)
    try:
        event.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict or exc.messages) from exc
    event.save()
    return event


def delete_event(*, event: Event, actor: User) -> None:
    _require_facilitator(actor)
    if event.created_by_id != actor.pk:
        raise ValidationError({"created_by": "You may only delete events you created."})
    event.delete()


def _active_enrollment_count_for_update(event_pk: int) -> int:
    agg = (
        Enrollment.objects.filter(event_id=event_pk, status=EnrollmentStatus.ENROLLED)
        .aggregate(n=Count("id"))
    )
    return int(agg["n"] or 0)


@transaction.atomic
def enroll_seeker(*, event: Event, seeker: User) -> Enrollment:
    """
    Enroll a seeker. Capacity counts only active (enrolled) rows; canceled rows do not count.
    Uses locking on the event row to serialize capacity checks with concurrent enrollments.
    """
    _require_seeker(seeker)

    locked_event = Event.objects.select_for_update().get(pk=event.pk)

    if Enrollment.objects.filter(
        event_id=locked_event.pk,
        seeker_id=seeker.pk,
        status=EnrollmentStatus.ENROLLED,
    ).exists():
        raise ValidationError("You are already enrolled in this event.")

    active_count = _active_enrollment_count_for_update(locked_event.pk)
    cap = locked_event.capacity
    if cap is not None and active_count >= cap:
        raise ValidationError("This event has reached its capacity.")

    try:
        return Enrollment.objects.create(
            event_id=locked_event.pk,
            seeker_id=seeker.pk,
            status=EnrollmentStatus.ENROLLED,
        )
    except IntegrityError as exc:
        raise ValidationError("You are already enrolled in this event.") from exc


@transaction.atomic
def cancel_enrollment(*, enrollment: Enrollment, seeker: User) -> Enrollment:
    locked = (
        Enrollment.objects.select_for_update()
        .select_related("event")
        .get(pk=enrollment.pk)
    )
    if locked.seeker_id != seeker.pk:
        raise ValidationError({"seeker": "You may only cancel your own enrollment."})
    if locked.status == EnrollmentStatus.CANCELED:
        return locked
    locked.status = EnrollmentStatus.CANCELED
    locked.save()
    return locked
