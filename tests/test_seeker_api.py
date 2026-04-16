from __future__ import annotations

import re
from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AccountProfile, AccountRole
from events.models import EnrollmentStatus
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


def _make_facilitator(email: str = "fac@example.com") -> User:
    user = User.objects.create_user(username=email, email=email, password="testpass123!")
    AccountProfile.objects.create(user=user, role=AccountRole.FACILITATOR, email_verified=True)
    return user


def assert_error_envelope(response):
    assert response.status_code in (400, 401, 403, 404, 405, 409, 429)
    body = response.json()
    assert "detail" in body
    assert "code" in body


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_event_list_ok(api_client):
    fac = _make_facilitator()
    now = timezone.now()
    create_event(
        title="A",
        description="",
        language="en",
        location="NYC",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=2),
        capacity=10,
        created_by=fac,
    )
    response = api_client.get("/api/events/")
    assert response.status_code == 200
    body = response.json()
    assert "count" in body and "next" in body and "previous" in body and "results" in body
    assert body["count"] == 1
    assert body["results"][0]["title"] == "A"


@pytest.mark.django_db
def test_event_detail_missing_returns_404(api_client):
    r = api_client.get("/api/events/999999999/")
    assert r.status_code == 404
    assert_error_envelope(r)


@pytest.mark.django_db
def test_event_detail_ok(api_client):
    fac = _make_facilitator()
    now = timezone.now()
    event = create_event(
        title="Detail",
        description="About",
        language="en",
        location="NYC",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=2),
        capacity=None,
        created_by=fac,
    )
    response = api_client.get(f"/api/events/{event.pk}/")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == event.pk
    assert data["title"] == "Detail"
    assert data["description"] == "About"


@pytest.mark.django_db
def test_event_filters_location_language_and_starts_range(api_client):
    fac = _make_facilitator()
    now = timezone.now()
    e1 = create_event(
        title="NYC en",
        description="",
        language="en",
        location="NYC",
        starts_at=now + timedelta(days=2),
        ends_at=now + timedelta(days=2, hours=1),
        capacity=10,
        created_by=fac,
    )
    create_event(
        title="LA es",
        description="",
        language="es",
        location="LA",
        starts_at=now + timedelta(days=3),
        ends_at=now + timedelta(days=3, hours=1),
        capacity=10,
        created_by=fac,
    )
    r = api_client.get("/api/events/", {"location": "nyc"})
    assert r.status_code == 200
    ids = {row["id"] for row in r.json()["results"]}
    assert ids == {e1.pk}

    r2 = api_client.get("/api/events/", {"language": "es"})
    assert r2.status_code == 200
    assert len(r2.json()["results"]) == 1
    assert r2.json()["results"][0]["location"] == "LA"

    r3 = api_client.get(
        "/api/events/",
        {
            "starts_after": (now + timedelta(days=1)).isoformat(),
            "starts_before": (now + timedelta(days=4)).isoformat(),
        },
    )
    assert r3.status_code == 200
    assert r3.json()["count"] == 2


@pytest.mark.django_db
def test_event_q_search_title_and_description(api_client):
    fac = _make_facilitator()
    now = timezone.now()
    create_event(
        title="Hidden",
        description="find-me-in-desc",
        language="en",
        location="X",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=1),
        capacity=10,
        created_by=fac,
    )
    create_event(
        title="find-me-in-title",
        description="",
        language="en",
        location="Y",
        starts_at=now + timedelta(days=2),
        ends_at=now + timedelta(days=2, hours=1),
        capacity=10,
        created_by=fac,
    )
    r = api_client.get("/api/events/", {"q": "find-me"})
    assert r.status_code == 200
    titles = {row["title"] for row in r.json()["results"]}
    assert "find-me-in-title" in titles
    r2 = api_client.get("/api/events/", {"q": "find-me-in-desc"})
    assert r2.status_code == 200
    assert r2.json()["count"] >= 1


@pytest.mark.django_db
def test_event_list_default_ordering_upcoming_first(api_client):
    fac = _make_facilitator()
    now = timezone.now()
    past = create_event(
        title="past",
        description="",
        language="en",
        location="Here",
        starts_at=now - timedelta(days=2),
        ends_at=now - timedelta(days=2) + timedelta(hours=2),
        capacity=10,
        created_by=fac,
    )
    future = create_event(
        title="future",
        description="",
        language="en",
        location="Here",
        starts_at=now + timedelta(days=2),
        ends_at=now + timedelta(days=2) + timedelta(hours=2),
        capacity=10,
        created_by=fac,
    )
    response = api_client.get("/api/events/")
    assert response.status_code == 200
    ids = [row["id"] for row in response.json()["results"]]
    assert ids.index(future.pk) < ids.index(past.pk)


@pytest.mark.django_db
def test_event_list_pagination_shape(api_client):
    fac = _make_facilitator()
    now = timezone.now()
    for i in range(3):
        create_event(
            title=f"E{i}",
            description="",
            language="en",
            location="Here",
            starts_at=now + timedelta(days=i + 1),
            ends_at=now + timedelta(days=i + 1) + timedelta(hours=1),
            capacity=10,
            created_by=fac,
        )
    r1 = api_client.get("/api/events/", {"page_size": 2})
    assert r1.status_code == 200
    body = r1.json()
    assert body["count"] == 3
    assert len(body["results"]) == 2
    assert body["next"] is not None
    assert body["previous"] is None


@pytest.mark.django_db
def test_seeker_enroll_success(api_client):
    _access_token(
        api_client,
        email="seek@example.com",
        password="StrongPass9!",
        role="seeker",
    )
    fac = _make_facilitator("fac2@example.com")
    now = timezone.now()
    event = create_event(
        title="Join",
        description="",
        language="en",
        location="Here",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=2),
        capacity=10,
        created_by=fac,
    )
    response = api_client.post(f"/api/events/{event.pk}/enroll/", {}, format="json")
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == EnrollmentStatus.ENROLLED
    assert data["event"]["id"] == event.pk


@pytest.mark.django_db
def test_verified_facilitator_blocked_from_upcoming_enrollments(api_client):
    _access_token(
        api_client,
        email="fac_me@example.com",
        password="StrongPass9!",
        role="facilitator",
    )
    r = api_client.get("/api/me/enrollments/upcoming/")
    assert r.status_code == 403
    assert_error_envelope(r)


@pytest.mark.django_db
def test_facilitator_cannot_enroll(api_client):
    _access_token(
        api_client,
        email="facuser@example.com",
        password="StrongPass9!",
        role="facilitator",
    )
    fac = _make_facilitator("owner@example.com")
    now = timezone.now()
    event = create_event(
        title="X",
        description="",
        language="en",
        location="Here",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=2),
        capacity=10,
        created_by=fac,
    )
    response = api_client.post(f"/api/events/{event.pk}/enroll/", {}, format="json")
    assert response.status_code == 403
    assert_error_envelope(response)


@pytest.mark.django_db
def test_enroll_capacity_full_returns_400_with_error_envelope():
    client_a = APIClient()
    _access_token(
        client_a,
        email="cap_a@example.com",
        password="StrongPass9!",
        role="seeker",
    )
    client_b = APIClient()
    _access_token(
        client_b,
        email="cap_b@example.com",
        password="StrongPass9!",
        role="seeker",
    )
    fac = _make_facilitator("fac-cap@example.com")
    now = timezone.now()
    event = create_event(
        title="Full",
        description="",
        language="en",
        location="Here",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=2),
        capacity=1,
        created_by=fac,
    )
    assert client_a.post(f"/api/events/{event.pk}/enroll/", {}, format="json").status_code == 201
    r2 = client_b.post(f"/api/events/{event.pk}/enroll/", {}, format="json")
    assert_error_envelope(r2)
    assert r2.status_code == 400
    body = r2.json()
    assert body["code"] == "validation_error"
    assert "capacity" in str(body["detail"]).lower()


@pytest.mark.django_db
def test_duplicate_active_enrollment_blocked(api_client):
    _access_token(
        api_client,
        email="dup@example.com",
        password="StrongPass9!",
        role="seeker",
    )
    fac = _make_facilitator("fac-dup@example.com")
    now = timezone.now()
    event = create_event(
        title="Dup",
        description="",
        language="en",
        location="Here",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=2),
        capacity=10,
        created_by=fac,
    )
    assert api_client.post(f"/api/events/{event.pk}/enroll/", {}, format="json").status_code == 201
    r2 = api_client.post(f"/api/events/{event.pk}/enroll/", {}, format="json")
    assert r2.status_code == 400
    assert_error_envelope(r2)


@pytest.mark.django_db
def test_cancel_missing_enrollment_returns_404(api_client):
    _access_token(
        api_client,
        email="miss_e@example.com",
        password="StrongPass9!",
        role="seeker",
    )
    r = api_client.post("/api/me/enrollments/999999999/cancel/", {}, format="json")
    assert r.status_code == 404
    assert_error_envelope(r)


@pytest.mark.django_db
def test_cancel_enrollment_success(api_client):
    _access_token(
        api_client,
        email="cancel@example.com",
        password="StrongPass9!",
        role="seeker",
    )
    fac = _make_facilitator("fac-can@example.com")
    now = timezone.now()
    event = create_event(
        title="Cancel me",
        description="",
        language="en",
        location="Here",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=2),
        capacity=10,
        created_by=fac,
    )
    enroll = api_client.post(f"/api/events/{event.pk}/enroll/", {}, format="json")
    eid = enroll.json()["id"]
    cancel = api_client.post(f"/api/me/enrollments/{eid}/cancel/", {}, format="json")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == EnrollmentStatus.CANCELED


@pytest.mark.django_db
def test_wrong_user_cannot_cancel_another_enrollment():
    client_a = APIClient()
    _access_token(
        client_a,
        email="a@example.com",
        password="StrongPass9!",
        role="seeker",
    )
    client_b = APIClient()
    _access_token(
        client_b,
        email="b@example.com",
        password="StrongPass9!",
        role="seeker",
    )
    fac = _make_facilitator("fac-w@example.com")
    now = timezone.now()
    event = create_event(
        title="Own",
        description="",
        language="en",
        location="Here",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=2),
        capacity=10,
        created_by=fac,
    )
    enroll = client_a.post(f"/api/events/{event.pk}/enroll/", {}, format="json")
    eid = enroll.json()["id"]

    wrong = client_b.post(f"/api/me/enrollments/{eid}/cancel/", {}, format="json")
    assert wrong.status_code == 403
    assert_error_envelope(wrong)


@pytest.mark.django_db
def test_upcoming_enrollments_only_future_active(api_client):
    _access_token(
        api_client,
        email="up@example.com",
        password="StrongPass9!",
        role="seeker",
    )
    fac = _make_facilitator("fac-up@example.com")
    now = timezone.now()
    future = create_event(
        title="Soon",
        description="",
        language="en",
        location="Here",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=2),
        capacity=10,
        created_by=fac,
    )
    past_event = create_event(
        title="Old",
        description="",
        language="en",
        location="Here",
        starts_at=now - timedelta(days=2),
        ends_at=now - timedelta(days=2) + timedelta(hours=2),
        capacity=10,
        created_by=fac,
    )
    api_client.post(f"/api/events/{future.pk}/enroll/", {}, format="json")
    api_client.post(f"/api/events/{past_event.pk}/enroll/", {}, format="json")

    upcoming = api_client.get("/api/me/enrollments/upcoming/")
    assert upcoming.status_code == 200
    body = upcoming.json()
    assert "count" in body and "results" in body
    ids = {row["event"]["id"] for row in body["results"]}
    assert future.pk in ids
    assert past_event.pk not in ids


@pytest.mark.django_db
def test_past_enrollments_only_past_active(api_client):
    _access_token(
        api_client,
        email="past@example.com",
        password="StrongPass9!",
        role="seeker",
    )
    fac = _make_facilitator("fac-past@example.com")
    now = timezone.now()
    future = create_event(
        title="Soon",
        description="",
        language="en",
        location="Here",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=2),
        capacity=10,
        created_by=fac,
    )
    past_event = create_event(
        title="Old",
        description="",
        language="en",
        location="Here",
        starts_at=now - timedelta(days=2),
        ends_at=now - timedelta(days=2) + timedelta(hours=2),
        capacity=10,
        created_by=fac,
    )
    api_client.post(f"/api/events/{future.pk}/enroll/", {}, format="json")
    api_client.post(f"/api/events/{past_event.pk}/enroll/", {}, format="json")

    past_resp = api_client.get("/api/me/enrollments/past/")
    assert past_resp.status_code == 200
    body = past_resp.json()
    ids = {row["event"]["id"] for row in body["results"]}
    assert past_event.pk in ids
    assert future.pk not in ids


@pytest.mark.django_db
def test_canceled_not_in_upcoming(api_client):
    _access_token(
        api_client,
        email="cx@example.com",
        password="StrongPass9!",
        role="seeker",
    )
    fac = _make_facilitator("fac-cx@example.com")
    now = timezone.now()
    future = create_event(
        title="Cx",
        description="",
        language="en",
        location="Here",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=2),
        capacity=10,
        created_by=fac,
    )
    enroll = api_client.post(f"/api/events/{future.pk}/enroll/", {}, format="json")
    eid = enroll.json()["id"]
    api_client.post(f"/api/me/enrollments/{eid}/cancel/", {}, format="json")

    upcoming = api_client.get("/api/me/enrollments/upcoming/")
    assert upcoming.status_code == 200
    assert upcoming.json()["count"] == 0


@pytest.mark.django_db
def test_unverified_seeker_blocked_for_seeker_endpoints(api_client):
    user = User.objects.create_user(
        username="unver@example.com",
        email="unver@example.com",
        password="StrongPass9!",
    )
    AccountProfile.objects.create(
        user=user,
        role=AccountRole.SEEKER,
        email_verified=False,
    )
    fac = _make_facilitator("fac-unver@example.com")
    now = timezone.now()
    event = create_event(
        title="Block",
        description="",
        language="en",
        location="Here",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=2),
        capacity=10,
        created_by=fac,
    )
    api_client.force_authenticate(user=user)
    enroll = api_client.post(f"/api/events/{event.pk}/enroll/", {}, format="json")
    assert enroll.status_code == 403
    assert_error_envelope(enroll)

    me = api_client.get("/api/me/enrollments/upcoming/")
    assert me.status_code == 403
    assert_error_envelope(me)


@pytest.mark.django_db
def test_unauthenticated_blocked_for_seeker_endpoints(api_client):
    fac = _make_facilitator("fac-anon@example.com")
    now = timezone.now()
    event = create_event(
        title="Anon",
        description="",
        language="en",
        location="Here",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=2),
        capacity=10,
        created_by=fac,
    )
    r = api_client.post(f"/api/events/{event.pk}/enroll/", {}, format="json")
    assert r.status_code == 401
    assert_error_envelope(r)

    r2 = api_client.get("/api/me/enrollments/upcoming/")
    assert r2.status_code == 401
    assert_error_envelope(r2)
