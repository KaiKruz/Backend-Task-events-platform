# Events Platform Backend

A submission-quality Django REST API for an events platform with email OTP verification, JWT auth, role-based access control, event discovery, and enrollments.

## Status
Phases 1–5 are complete and implemented:

- **Phase 2:** Auth + OTP (signup, verify-email, JWT login/refresh) on Django’s default `User` with `AccountProfile` + `EmailOTP`.
- **Phase 3:** `Event` and `Enrollment` models, including a **database-level unique constraint** so a seeker can have only one **active** (`enrolled`) row per event. Model and service behavior (validation, enrollment, capacity, cancellation) is covered by tests under `tests/test_events.py` (pytest).
- **Phase 4:** Seeker-facing event discovery and enrollment HTTP APIs (see below). Covered by `tests/test_seeker_api.py`.
- **Phase 5:** Facilitator event management APIs (create/list/detail/update/delete/my-summary) with verified facilitator gating, ownership enforcement, and service-backed validation/error handling. Covered by `tests/test_facilitator_api.py`.

### Seeker / public events API (Phase 4)

Public (no auth):

- `GET /api/events/` — paginated list (`count`, `next`, `previous`, `results`). Default ordering: **not-yet-started events first**, then by `starts_at` ascending. Query params: `location`, `language` (case-insensitive **exact** match on the full stored value—same semantics as Django `iexact`, not substring), `starts_after`, `starts_before` (ISO datetimes), `q` (substring match on title or description), optional `ordering`, `page`, `page_size`.
- `GET /api/events/{id}/` — event detail.

Verified seeker only (JWT `Authorization: Bearer <access>`; `seeker` role; email verified):

- `POST /api/events/{id}/enroll/` — enroll in an event (delegates to `enroll_seeker`). Facilitators and unverified users are rejected.
- `GET /api/me/enrollments/upcoming/` — active (`enrolled`) enrollments whose event `starts_at` is **≥ now** (UTC).
- `GET /api/me/enrollments/past/` — active enrollments whose event `starts_at` is **< now** (UTC).
- `POST /api/me/enrollments/{id}/cancel/` — cancel own enrollment (delegates to `cancel_enrollment`).

Verified facilitator only (JWT `Authorization: Bearer <access>`; `facilitator` role; email verified):

- `POST /api/facilitator/events/` — create an event owned by the authenticated facilitator.
- `GET /api/facilitator/events/` — list only events created by the authenticated facilitator.
- `GET /api/facilitator/events/{id}/` — retrieve own event only.
- `PATCH /api/facilitator/events/{id}/` — partially update own event only.
- `DELETE /api/facilitator/events/{id}/` — delete own event only.
- `GET /api/facilitator/events/my-summary/` — per owned event: `total_active_enrollments` (status=`enrolled` only) and `available_seats` (`null` when capacity is unlimited).

Postman: `postman/EventsPlatform.postman_collection.json` (collection variables: `base_url`, `access_token`, `refresh_token`, `event_id`, `enrollment_id`).

## Local setup (Windows / PowerShell)

**Python:** Use **3.12 or newer**. The repo’s Ruff config targets Python 3.12 (`pyproject.toml`); use 3.12+ for consistent lint behavior.

Create and activate a virtualenv:

```bash
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements\dev.txt
```

Environment variables:

- Copy `.env.example` to `.env` and adjust values for your machine.
- `DATABASE_URL` should point at PostgreSQL for real usage.
- `DJANGO_SECRET_KEY` should be a long random string in development and automated tests; very short placeholder values can trigger Django’s security warnings about `SECRET_KEY`.

Run (validation / local CI-style checks):

```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
pytest
ruff check .
python manage.py makemigrations --check
```

The `makemigrations --check` step fails if model changes are not reflected in migrations (useful before commits).

Health endpoint:

- `GET /api/health/` → `200 { "status": "ok" }`

Auth endpoints (JSON):

- `POST /api/auth/signup/` — body: `email`, `password`, `role` (`seeker` | `facilitator`) → `201` with `email`, `role`; sends a 6-digit OTP email (console backend by default)
- `POST /api/auth/verify-email/` — body: `email`, `otp` → `200` when verified
- `POST /api/auth/login/` — body: `email`, `password` → `200` with `access`, `refresh` (requires verified email)
- `POST /api/auth/refresh/` — body: `refresh` → `200` with a new `access` token (SimpleJWT refresh flow)

## Assignment goals
Build a backend that supports:

- signup with `email`, `password`, and `role`
- email OTP verification before login
- JWT authentication
- roles: `seeker` and `facilitator`
- event search and filtering
- event enrollment and cancellation
- facilitator-owned event CRUD
- PostgreSQL migrations and indexes
- README and Postman documentation

## Non-negotiable constraints
- Use Django's default `auth.User` model only
- Do **not** expose or require `username` in API payloads
- Login must use `email + password`
- Unverified users must not be able to log in
- Enforce role and ownership checks
- Use timezone-aware UTC-safe datetimes
- Return errors in this shape:

```json
{ "detail": "message", "code": "error_code" }
```