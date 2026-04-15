# Events Platform Backend

A submission-quality Django REST API for an events platform with email OTP verification, JWT auth, role-based access control, event discovery, and enrollments.

## Status
Phase 1 scaffold complete (Django + DRF + SimpleJWT + Postgres-ready settings).

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

Run:

```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
pytest
ruff check .
```

Health endpoint:

- `GET /api/health/` → `200 { "status": "ok" }`

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