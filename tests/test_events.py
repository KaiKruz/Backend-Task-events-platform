from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError as DRFValidationError

from accounts.models import AccountProfile, AccountRole
from events.models import Enrollment, EnrollmentStatus, Event
from events.services import cancel_enrollment, create_event, enroll_seeker


def _make_user(*, email: str, role: str) -> User:
    user = User.objects.create_user(username=email, email=email, password="testpass123!")
    AccountProfile.objects.create(user=user, role=role, email_verified=True)
    return user


def _event_times():
    starts = timezone.now() + timedelta(days=1)
    ends = starts + timedelta(hours=2)
    return starts, ends


@pytest.mark.django_db
def test_event_full_clean_rejects_capacity_zero():
    facilitator = _make_user(email="fac-cap0@example.com", role=AccountRole.FACILITATOR)
    starts, ends = _event_times()
    event = Event(
        title="Bad cap",
        description="",
        language="en",
        location="NYC",
        starts_at=starts,
        ends_at=ends,
        capacity=0,
        created_by=facilitator,
    )
    with pytest.raises(DjangoValidationError) as exc:
        event.full_clean()
    assert "capacity" in exc.value.error_dict


@pytest.mark.django_db
def test_event_full_clean_rejects_ends_at_before_starts_at():
    facilitator = _make_user(email="fac@example.com", role=AccountRole.FACILITATOR)
    starts, ends = _event_times()
    event = Event(
        title="Workshop",
        description="",
        language="en",
        location="NYC",
        starts_at=starts,
        ends_at=starts - timedelta(minutes=1),
        capacity=None,
        created_by=facilitator,
    )
    with pytest.raises(DjangoValidationError) as exc:
        event.full_clean()
    assert "ends_at" in exc.value.error_dict


@pytest.mark.django_db
def test_event_db_rejects_ends_at_not_after_starts_at():
    facilitator = _make_user(email="fac2@example.com", role=AccountRole.FACILITATOR)
    starts, _ = _event_times()
    with pytest.raises(IntegrityError):
        Event.objects.create(
            title="Bad",
            description="",
            language="en",
            location="NYC",
            starts_at=starts,
            ends_at=starts,
            capacity=None,
            created_by=facilitator,
        )


@pytest.mark.django_db
def test_create_event_requires_facilitator():
    seeker = _make_user(email="seek@example.com", role=AccountRole.SEEKER)
    starts, ends = _event_times()
    with pytest.raises(DRFValidationError):
        create_event(
            title="X",
            description="",
            language="en",
            location="Here",
            starts_at=starts,
            ends_at=ends,
            capacity=10,
            created_by=seeker,
        )


@pytest.mark.django_db
def test_duplicate_active_enrollment_blocked_by_service():
    facilitator = _make_user(email="fac3@example.com", role=AccountRole.FACILITATOR)
    seeker = _make_user(email="seek3@example.com", role=AccountRole.SEEKER)
    starts, ends = _event_times()
    event = create_event(
        title="E1",
        description="",
        language="en",
        location="NYC",
        starts_at=starts,
        ends_at=ends,
        capacity=10,
        created_by=facilitator,
    )
    enroll_seeker(event=event, seeker=seeker)
    with pytest.raises(DRFValidationError):
        enroll_seeker(event=event, seeker=seeker)


@pytest.mark.django_db
def test_duplicate_active_enrollment_blocked_at_db_level():
    facilitator = _make_user(email="fac4@example.com", role=AccountRole.FACILITATOR)
    seeker = _make_user(email="seek4@example.com", role=AccountRole.SEEKER)
    starts, ends = _event_times()
    event = create_event(
        title="E2",
        description="",
        language="en",
        location="NYC",
        starts_at=starts,
        ends_at=ends,
        capacity=10,
        created_by=facilitator,
    )
    Enrollment.objects.create(
        event=event,
        seeker=seeker,
        status=EnrollmentStatus.ENROLLED,
    )
    with pytest.raises(IntegrityError):
        Enrollment.objects.create(
            event=event,
            seeker=seeker,
            status=EnrollmentStatus.ENROLLED,
        )


@pytest.mark.django_db
def test_cancel_enrollment_rejects_wrong_seeker():
    facilitator = _make_user(email="fac-wrong@example.com", role=AccountRole.FACILITATOR)
    seeker = _make_user(email="seek-wrong@example.com", role=AccountRole.SEEKER)
    other = _make_user(email="other-wrong@example.com", role=AccountRole.SEEKER)
    starts, ends = _event_times()
    event = create_event(
        title="E-wrong",
        description="",
        language="en",
        location="NYC",
        starts_at=starts,
        ends_at=ends,
        capacity=10,
        created_by=facilitator,
    )
    enrollment = enroll_seeker(event=event, seeker=seeker)
    with pytest.raises(DRFValidationError) as exc:
        cancel_enrollment(enrollment=enrollment, seeker=other)
    assert "seeker" in exc.value.detail


@pytest.mark.django_db
def test_canceled_enrollment_allows_re_enrollment():
    facilitator = _make_user(email="fac5@example.com", role=AccountRole.FACILITATOR)
    seeker = _make_user(email="seek5@example.com", role=AccountRole.SEEKER)
    starts, ends = _event_times()
    event = create_event(
        title="E3",
        description="",
        language="en",
        location="NYC",
        starts_at=starts,
        ends_at=ends,
        capacity=1,
        created_by=facilitator,
    )
    first = enroll_seeker(event=event, seeker=seeker)
    cancel_enrollment(enrollment=first, seeker=seeker)
    second = enroll_seeker(event=event, seeker=seeker)
    assert first.pk != second.pk
    assert Enrollment.objects.filter(event=event, seeker=seeker, status=EnrollmentStatus.CANCELED).exists()
    assert Enrollment.objects.filter(event=event, seeker=seeker, status=EnrollmentStatus.ENROLLED).exists()


@pytest.mark.django_db
def test_capacity_enforced():
    facilitator = _make_user(email="fac6@example.com", role=AccountRole.FACILITATOR)
    s1 = _make_user(email="s1@example.com", role=AccountRole.SEEKER)
    s2 = _make_user(email="s2@example.com", role=AccountRole.SEEKER)
    starts, ends = _event_times()
    event = create_event(
        title="Small",
        description="",
        language="en",
        location="NYC",
        starts_at=starts,
        ends_at=ends,
        capacity=1,
        created_by=facilitator,
    )
    enroll_seeker(event=event, seeker=s1)
    with pytest.raises(DRFValidationError) as exc:
        enroll_seeker(event=event, seeker=s2)
    assert "capacity" in str(exc.value.detail).lower()


@pytest.mark.django_db
def test_null_capacity_allows_unlimited_enrollments():
    facilitator = _make_user(email="fac7@example.com", role=AccountRole.FACILITATOR)
    starts, ends = _event_times()
    event = create_event(
        title="Open",
        description="",
        language="en",
        location="NYC",
        starts_at=starts,
        ends_at=ends,
        capacity=None,
        created_by=facilitator,
    )
    for i in range(5):
        u = _make_user(email=f"bulk{i}@example.com", role=AccountRole.SEEKER)
        enroll_seeker(event=event, seeker=u)
    assert (
        Enrollment.objects.filter(event=event, status=EnrollmentStatus.ENROLLED).count() == 5
    )


@pytest.mark.django_db
def test_canceled_enrollment_frees_capacity_for_another_seeker():
    facilitator = _make_user(email="fac8@example.com", role=AccountRole.FACILITATOR)
    a = _make_user(email="a8@example.com", role=AccountRole.SEEKER)
    b = _make_user(email="b8@example.com", role=AccountRole.SEEKER)
    starts, ends = _event_times()
    event = create_event(
        title="One seat",
        description="",
        language="en",
        location="NYC",
        starts_at=starts,
        ends_at=ends,
        capacity=1,
        created_by=facilitator,
    )
    ea = enroll_seeker(event=event, seeker=a)
    with pytest.raises(DRFValidationError):
        enroll_seeker(event=event, seeker=b)
    cancel_enrollment(enrollment=ea, seeker=a)
    enroll_seeker(event=event, seeker=b)


@pytest.mark.django_db
def test_canceled_records_do_not_count_toward_capacity():
    facilitator = _make_user(email="fac9@example.com", role=AccountRole.FACILITATOR)
    seeker = _make_user(email="seek9@example.com", role=AccountRole.SEEKER)
    starts, ends = _event_times()
    event = create_event(
        title="Recycle",
        description="",
        language="en",
        location="NYC",
        starts_at=starts,
        ends_at=ends,
        capacity=1,
        created_by=facilitator,
    )
    first = enroll_seeker(event=event, seeker=seeker)
    cancel_enrollment(enrollment=first, seeker=seeker)
    enroll_seeker(event=event, seeker=seeker)
    active = Enrollment.objects.filter(event=event, status=EnrollmentStatus.ENROLLED).count()
    assert active == 1


@pytest.mark.django_db(transaction=True)
def test_enrollment_writes_roll_back_with_outer_transaction_failure():
    facilitator = _make_user(email="fac10@example.com", role=AccountRole.FACILITATOR)
    seeker = _make_user(email="seek10@example.com", role=AccountRole.SEEKER)
    starts, ends = _event_times()
    event = create_event(
        title="Tx",
        description="",
        language="en",
        location="NYC",
        starts_at=starts,
        ends_at=ends,
        capacity=10,
        created_by=facilitator,
    )
    with pytest.raises(RuntimeError, match="boom"):
        with transaction.atomic():
            enroll_seeker(event=event, seeker=seeker)
            raise RuntimeError("boom")
    assert not Enrollment.objects.filter(event=event, seeker=seeker).exists()
