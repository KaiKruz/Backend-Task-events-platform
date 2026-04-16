from __future__ import annotations

import re
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AccountProfile, AccountRole
from events.models import Enrollment, EnrollmentStatus, Event
from events.services import create_event


def _otp_from_last_email() -> str:
    assert len(mail.outbox) >= 1
    match = re.search(r"\b(\d{6})\b", mail.outbox[-1].body)
    assert match is not None
    return match.group(1)


def _access_token(api_client: APIClient, *, email: str, password: str, role: str) -> str:
    assert (
        api_client.post(
            "/api/auth/signup/",
            {"email": email, "password": password, "role": role},
            format="json",
        ).status_code
        == 201
    )
    otp = _otp_from_last_email()
    assert (
        api_client.post(
            "/api/auth/verify-email/",
            {"email": email, "otp": otp},
            format="json",
        ).status_code
        == 200
    )
    login = api_client.post(
        "/api/auth/login/",
        {"email": email, "password": password},
        format="json",
    )
    assert login.status_code == 200
    access = login.json()["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return access


def _make_user(*, email: str, role: str) -> User:
    user = User.objects.create_user(username=email, email=email, password="testpass123!")
    AccountProfile.objects.create(user=user, role=role, email_verified=True)
    return user


def assert_error_envelope(response):
    assert response.status_code in (400, 401, 403, 404, 405, 409, 429)
    body = response.json()
    assert "detail" in body
    assert "code" in body


@pytest.fixture
def api_client():
    return APIClient()


def _event_payload(*, title: str = "Facilitator Event", capacity=25):
    now = timezone.now()
    return {
        "title": title,
        "description": "Deep dive",
        "language": "en",
        "location": "Cairo",
        "starts_at": (now + timedelta(days=3)).isoformat(),
        "ends_at": (now + timedelta(days=3, hours=2)).isoformat(),
        "capacity": capacity,
    }


@pytest.mark.django_db
def test_facilitator_can_create_event(api_client):
    _access_token(
        api_client,
        email="fac-create@example.com",
        password="StrongPass9!",
        role="facilitator",
    )
    response = api_client.post("/api/facilitator/events/", _event_payload(), format="json")
    assert response.status_code == 201
    assert response.json()["title"] == "Facilitator Event"


@pytest.mark.django_db
def test_created_by_payload_cannot_spoof_creator(api_client):
    owner = _make_user(email="fac-owner@example.com", role=AccountRole.FACILITATOR)
    attacker_target = _make_user(
        email="fac-target@example.com",
        role=AccountRole.FACILITATOR,
    )
    api_client.force_authenticate(owner)
    payload = _event_payload(title="Owned by requester")
    payload["created_by"] = attacker_target.pk

    response = api_client.post("/api/facilitator/events/", payload, format="json")
    assert response.status_code == 201
    event = Event.objects.get(pk=response.json()["id"])
    assert event.created_by_id == owner.pk
    assert event.created_by_id != attacker_target.pk


@pytest.mark.django_db
def test_seeker_cannot_create_event(api_client):
    _access_token(
        api_client,
        email="seek-create@example.com",
        password="StrongPass9!",
        role="seeker",
    )
    response = api_client.post("/api/facilitator/events/", _event_payload(), format="json")
    assert response.status_code == 403
    assert_error_envelope(response)


@pytest.mark.django_db
def test_unauthenticated_cannot_create_event(api_client):
    response = api_client.post("/api/facilitator/events/", _event_payload(), format="json")
    assert response.status_code == 401
    assert_error_envelope(response)


@pytest.mark.django_db
def test_facilitator_list_returns_only_own_events(api_client):
    owner = _make_user(email="owner-list@example.com", role=AccountRole.FACILITATOR)
    other = _make_user(email="other-list@example.com", role=AccountRole.FACILITATOR)
    now = timezone.now()
    own = create_event(
        title="Mine",
        description="",
        language="en",
        location="A",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=1),
        capacity=10,
        created_by=owner,
    )
    create_event(
        title="Not mine",
        description="",
        language="en",
        location="B",
        starts_at=now + timedelta(days=2),
        ends_at=now + timedelta(days=2, hours=1),
        capacity=10,
        created_by=other,
    )
    api_client.force_authenticate(owner)

    response = api_client.get("/api/facilitator/events/")
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()["results"]}
    assert ids == {own.pk}


@pytest.mark.django_db
def test_facilitator_detail_returns_own_event(api_client):
    owner = _make_user(email="owner-detail@example.com", role=AccountRole.FACILITATOR)
    now = timezone.now()
    event = create_event(
        title="Own detail",
        description="",
        language="en",
        location="A",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=1),
        capacity=10,
        created_by=owner,
    )
    api_client.force_authenticate(owner)
    response = api_client.get(f"/api/facilitator/events/{event.pk}/")
    assert response.status_code == 200
    assert response.json()["id"] == event.pk


@pytest.mark.django_db
def test_facilitator_cannot_retrieve_another_facilitators_event(api_client):
    owner = _make_user(email="owner-r@example.com", role=AccountRole.FACILITATOR)
    other = _make_user(email="other-r@example.com", role=AccountRole.FACILITATOR)
    now = timezone.now()
    event = create_event(
        title="Private",
        description="",
        language="en",
        location="A",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=1),
        capacity=10,
        created_by=owner,
    )
    api_client.force_authenticate(other)
    response = api_client.get(f"/api/facilitator/events/{event.pk}/")
    assert response.status_code == 404
    assert_error_envelope(response)


@pytest.mark.django_db
def test_facilitator_can_patch_own_event(api_client):
    owner = _make_user(email="owner-p@example.com", role=AccountRole.FACILITATOR)
    now = timezone.now()
    event = create_event(
        title="Before",
        description="",
        language="en",
        location="A",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=1),
        capacity=10,
        created_by=owner,
    )
    api_client.force_authenticate(owner)
    response = api_client.patch(
        f"/api/facilitator/events/{event.pk}/",
        {"title": "After"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["title"] == "After"


@pytest.mark.django_db
def test_facilitator_cannot_patch_another_facilitators_event(api_client):
    owner = _make_user(email="owner-p2@example.com", role=AccountRole.FACILITATOR)
    other = _make_user(email="other-p2@example.com", role=AccountRole.FACILITATOR)
    now = timezone.now()
    event = create_event(
        title="No patch",
        description="",
        language="en",
        location="A",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=1),
        capacity=10,
        created_by=owner,
    )
    api_client.force_authenticate(other)
    response = api_client.patch(
        f"/api/facilitator/events/{event.pk}/",
        {"title": "Bad"},
        format="json",
    )
    assert response.status_code == 404
    assert_error_envelope(response)


@pytest.mark.django_db
def test_facilitator_can_delete_own_event(api_client):
    owner = _make_user(email="owner-d@example.com", role=AccountRole.FACILITATOR)
    now = timezone.now()
    event = create_event(
        title="Delete me",
        description="",
        language="en",
        location="A",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=1),
        capacity=10,
        created_by=owner,
    )
    api_client.force_authenticate(owner)
    response = api_client.delete(f"/api/facilitator/events/{event.pk}/")
    assert response.status_code == 204


@pytest.mark.django_db
def test_facilitator_cannot_delete_another_facilitators_event(api_client):
    owner = _make_user(email="owner-d2@example.com", role=AccountRole.FACILITATOR)
    other = _make_user(email="other-d2@example.com", role=AccountRole.FACILITATOR)
    now = timezone.now()
    event = create_event(
        title="Keep me",
        description="",
        language="en",
        location="A",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=1),
        capacity=10,
        created_by=owner,
    )
    api_client.force_authenticate(other)
    response = api_client.delete(f"/api/facilitator/events/{event.pk}/")
    assert response.status_code == 404
    assert_error_envelope(response)


@pytest.mark.django_db
def test_seeker_cannot_access_facilitator_list_detail_update_delete(api_client):
    _access_token(
        api_client,
        email="seek-guard@example.com",
        password="StrongPass9!",
        role="seeker",
    )
    owner = _make_user(email="owner-guard@example.com", role=AccountRole.FACILITATOR)
    now = timezone.now()
    event = create_event(
        title="Owner event",
        description="",
        language="en",
        location="A",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=1),
        capacity=10,
        created_by=owner,
    )
    list_response = api_client.get("/api/facilitator/events/")
    detail_response = api_client.get(f"/api/facilitator/events/{event.pk}/")
    patch_response = api_client.patch(
        f"/api/facilitator/events/{event.pk}/",
        {"title": "No"},
        format="json",
    )
    delete_response = api_client.delete(f"/api/facilitator/events/{event.pk}/")
    for response in (list_response, detail_response, patch_response, delete_response):
        assert response.status_code == 403
        assert_error_envelope(response)


@pytest.mark.django_db
def test_seeker_denied_my_summary(api_client):
    _access_token(
        api_client,
        email="seek-summary-denied@example.com",
        password="StrongPass9!",
        role="seeker",
    )
    response = api_client.get("/api/facilitator/events/my-summary/")
    assert response.status_code == 403
    assert_error_envelope(response)


@pytest.mark.django_db
def test_unverified_facilitator_denied_facilitator_endpoints(api_client):
    user = User.objects.create_user(
        username="fac-unverified@example.com",
        email="fac-unverified@example.com",
        password="StrongPass9!",
    )
    AccountProfile.objects.create(
        user=user,
        role=AccountRole.FACILITATOR,
        email_verified=False,
    )
    api_client.force_authenticate(user)

    list_response = api_client.get("/api/facilitator/events/")
    summary_response = api_client.get("/api/facilitator/events/my-summary/")
    create_response = api_client.post(
        "/api/facilitator/events/",
        _event_payload(),
        format="json",
    )
    for response in (list_response, summary_response, create_response):
        assert response.status_code == 403
        assert_error_envelope(response)


@pytest.mark.django_db
def test_invalid_facilitator_create_payload_returns_400_envelope(api_client):
    _access_token(
        api_client,
        email="fac-invalid-create@example.com",
        password="StrongPass9!",
        role="facilitator",
    )
    now = timezone.now()
    payload = _event_payload(title="Invalid create")
    payload["starts_at"] = (now + timedelta(days=4)).isoformat()
    payload["ends_at"] = (now + timedelta(days=4)).isoformat()

    response = api_client.post("/api/facilitator/events/", payload, format="json")
    assert response.status_code == 400
    assert_error_envelope(response)
    assert "ends_at" in response.json()["detail"]


@pytest.mark.django_db
def test_invalid_facilitator_update_payload_returns_400_envelope(api_client):
    owner = _make_user(email="owner-invalid-update@example.com", role=AccountRole.FACILITATOR)
    now = timezone.now()
    event = create_event(
        title="Before invalid update",
        description="",
        language="en",
        location="A",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=1),
        capacity=10,
        created_by=owner,
    )
    api_client.force_authenticate(owner)
    response = api_client.patch(
        f"/api/facilitator/events/{event.pk}/",
        {"capacity": 0},
        format="json",
    )
    assert response.status_code == 400
    assert_error_envelope(response)
    assert "capacity" in response.json()["detail"]


@pytest.mark.django_db
def test_my_summary_returns_correct_active_counts_and_available_seats(api_client):
    facilitator = _make_user(email="fac-summary@example.com", role=AccountRole.FACILITATOR)
    seeker_a = _make_user(email="seek-a@example.com", role=AccountRole.SEEKER)
    seeker_b = _make_user(email="seek-b@example.com", role=AccountRole.SEEKER)
    seeker_c = _make_user(email="seek-c@example.com", role=AccountRole.SEEKER)
    now = timezone.now()
    capped = create_event(
        title="Capped",
        description="",
        language="en",
        location="A",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=1),
        capacity=3,
        created_by=facilitator,
    )
    unlimited = create_event(
        title="Unlimited",
        description="",
        language="en",
        location="A",
        starts_at=now + timedelta(days=2),
        ends_at=now + timedelta(days=2, hours=1),
        capacity=None,
        created_by=facilitator,
    )

    Enrollment.objects.create(event=capped, seeker=seeker_a, status=EnrollmentStatus.ENROLLED)
    Enrollment.objects.create(event=capped, seeker=seeker_b, status=EnrollmentStatus.ENROLLED)
    Enrollment.objects.create(event=capped, seeker=seeker_c, status=EnrollmentStatus.CANCELED)
    Enrollment.objects.create(event=unlimited, seeker=seeker_a, status=EnrollmentStatus.ENROLLED)

    api_client.force_authenticate(facilitator)
    response = api_client.get("/api/facilitator/events/my-summary/")
    assert response.status_code == 200
    rows = {row["id"]: row for row in response.json()["results"]}

    assert rows[capped.pk]["total_active_enrollments"] == 2
    assert rows[capped.pk]["available_seats"] == 1
    assert rows[unlimited.pk]["total_active_enrollments"] == 1
    assert rows[unlimited.pk]["available_seats"] is None


@pytest.mark.django_db
def test_my_summary_returns_only_owned_events(api_client):
    owner = _make_user(email="owner-scope@example.com", role=AccountRole.FACILITATOR)
    other = _make_user(email="other-scope@example.com", role=AccountRole.FACILITATOR)
    now = timezone.now()
    own = create_event(
        title="Mine",
        description="",
        language="en",
        location="A",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=1),
        capacity=2,
        created_by=owner,
    )
    create_event(
        title="Other",
        description="",
        language="en",
        location="B",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=1),
        capacity=2,
        created_by=other,
    )
    api_client.force_authenticate(owner)
    response = api_client.get("/api/facilitator/events/my-summary/")
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()["results"]}
    assert ids == {own.pk}


@pytest.mark.django_db
def test_facilitator_delete_uses_service_backed_flow(api_client):
    owner = _make_user(email="owner-service-delete@example.com", role=AccountRole.FACILITATOR)
    now = timezone.now()
    event = create_event(
        title="Delete through service",
        description="",
        language="en",
        location="A",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=1),
        capacity=10,
        created_by=owner,
    )
    api_client.force_authenticate(owner)

    with patch("events.views.delete_event") as mocked_delete_event:
        response = api_client.delete(f"/api/facilitator/events/{event.pk}/")

    assert response.status_code == 204
    mocked_delete_event.assert_called_once_with(event=event, actor=owner)
