# Events Platform Backend

Submission-quality Django REST API for an events platform with email OTP verification, JWT auth, role-based access control, event discovery, seeker enrollments, and facilitator-owned event management.

## Project overview

This project implements the core assignment through Phase 5 and completes Phase 6 documentation/submission polish. It keeps Django's default `auth.User`, adds profile/OTP/event/enrollment domain models, and exposes REST endpoints for auth, discovery, enrollment, and facilitator workflows.

## Current phase and completion status

- Phase 1: Scaffold and project setup - complete
- Phase 2: Auth + OTP - complete
- Phase 3: Events + enrollments models/services - complete
- Phase 4: Public + seeker APIs - complete
- Phase 5: Facilitator APIs - complete
- Phase 6: Final docs and submission polish - complete
- Phase 7 (bonus): not started

## Implemented features (through Phase 5)

- Signup with `email`, `password`, and `role` (`seeker` | `facilitator`)
- OTP email verification before login
- JWT login/refresh using email + password (no username in payloads)
- Unverified users blocked from login and protected endpoints
- Public event list/detail with filters and pagination
- Seeker enrollment, upcoming/past enrollment views, and cancellation
- Facilitator create/list/detail/patch/delete for own events only
- Facilitator summary endpoint with active enrollment counts and available seats
- Assignment error envelope and pagination shape compliance

## Stack used

- Python 3.12+
- Django + Django REST Framework
- SimpleJWT (`djangorestframework-simplejwt`)
- `django-filter`
- `django-environ`
- PostgreSQL (assignment target) with SQLite fallback for local convenience
- Pytest + pytest-django
- Ruff

## Setup instructions

### 1) Create and activate a virtual environment (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 1b) Create and activate a virtual environment (bash)

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies (PowerShell)

```powershell
pip install -r requirements\dev.txt
```

### 2b) Install dependencies (bash)

```bash
pip install -r requirements/dev.txt
```

### 3) Configure environment variables

- Copy `.env.example` to `.env`.
- `.env` is local-only and should never be committed.
- `.env.example` is the committed template for reviewers and teammates.

```powershell
Copy-Item .env.example .env
```

```bash
cp .env.example .env
```

### 4) Database setup notes

- Assignment target DB is PostgreSQL via `DATABASE_URL`.
- Current project also supports SQLite fallback when `DATABASE_URL` is unset (`db.sqlite3`) to make local checks easy.
- For submission/reviewer parity, prefer setting `DATABASE_URL` to PostgreSQL.

## Environment variables

See `.env.example` for complete template. Main variables:

- `DJANGO_SETTINGS_MODULE` (default local settings module)
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DATABASE_URL`
- `DEFAULT_FROM_EMAIL`
- `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`
- `PAGE_SIZE`
- `ACCESS_TOKEN_LIFETIME_MINUTES`, `REFRESH_TOKEN_LIFETIME_DAYS`
- `JWT_SIGNING_KEY`
- `OTP_EXPIRY_MINUTES`, `OTP_MAX_ATTEMPTS`, `OTP_RESEND_COOLDOWN_SECONDS`

## Run commands

```bash
python manage.py migrate
python manage.py runserver
```

Health endpoint:

- `GET /api/health/` -> `200 {"status":"ok"}`

## Migration commands

```bash
python manage.py makemigrations
python manage.py makemigrations --check
python manage.py migrate
```

## Test commands

```bash
python -m pytest -q
```

## Lint/check commands

```bash
python -m ruff check .
python manage.py check
python manage.py makemigrations --check
```

## Authentication flow summary

1. `POST /api/auth/signup/` with `email`, `password`, `role`.
2. Read OTP (console email backend by default in local setup).
3. `POST /api/auth/verify-email/` with `email`, `otp`.
4. `POST /api/auth/login/` with `email`, `password` to receive `access` + `refresh`.
5. Send `Authorization: Bearer <access>` to protected endpoints.
6. `POST /api/auth/refresh/` with `refresh` to obtain a new access token.

Rules enforced:

- No `username` field in signup/login payloads.
- Unverified users cannot log in.
- Role checks (`seeker` vs `facilitator`) and ownership checks are enforced on protected routes.

## Endpoint summary

### Auth

- `POST /api/auth/signup/`
- `POST /api/auth/verify-email/`
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`

### Public / seeker

- `GET /api/events/` (public; filter + pagination)
- `GET /api/events/{id}/` (public)
- `POST /api/events/{id}/enroll/` (verified seeker)
- `GET /api/me/enrollments/upcoming/` (verified seeker)
- `GET /api/me/enrollments/past/` (verified seeker)
- `POST /api/me/enrollments/{id}/cancel/` (verified seeker; own enrollment)

### Facilitator

- `POST /api/facilitator/events/` (verified facilitator)
- `GET /api/facilitator/events/` (own events)
- `GET /api/facilitator/events/{id}/` (own event)
- `PATCH /api/facilitator/events/{id}/` (own event)
- `DELETE /api/facilitator/events/{id}/` (own event)
- `GET /api/facilitator/events/my-summary/` (own events with active counts/available seats)

## Design decisions

- Keep Django default `User` and extend behavior with `AccountProfile`.
- Keep views thin; put business logic in services.
- Use explicit permission classes for role/verification/ownership checks.
- Normalize API failures to assignment envelope: `{"detail": ..., "code": ...}`.
- Enforce one active enrollment per seeker/event at DB level.
- Use timezone-aware datetimes (UTC).

## Tradeoffs / notes

- SQLite fallback is enabled for easy local setup; PostgreSQL remains the assignment target.
- OTP delivery uses console backend by default for dev speed and deterministic tests.
- No bonus scope (Docker/Celery/deployment/scheduled mail) is implemented in this phase.

## Postman collection

Use `postman/EventsPlatform.postman_collection.json`.

Collection variables:

- `base_url`
- `access_token`
- `refresh_token`
- `event_id`
- `enrollment_id`
- `facilitator_event_id`

Suggested flow:

1. Run Auth requests.
2. Use seeker token for seeker endpoints.
3. Use facilitator token for facilitator endpoints.