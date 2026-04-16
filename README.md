# Events Platform Backend

A submission-quality Django REST API for an events platform with email OTP verification, JWT auth, role-based access control, event discovery, and enrollments.

## Status
Phases 1–3 are implemented:

- **Phase 2:** Auth + OTP (signup, verify-email, JWT login/refresh) on Django’s default `User` with `AccountProfile` + `EmailOTP`.
- **Phase 3:** `Event` and `Enrollment` models, including a **database-level unique constraint** so a seeker can have only one **active** (`enrolled`) row per event. Model and service behavior (validation, enrollment, capacity, cancellation) is covered by tests under `tests/test_events.py` (pytest).

API endpoints for events and enrollments are planned for Phase 4+; this phase delivers the data layer and service logic tested in isolation.

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