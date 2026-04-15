---
name: django-events-backend
overview: Build a submission-ready Django REST API for an Events Platform using default Django User, DRF, JWT, and PostgreSQL, with email+OTP verification gating login, role/ownership permissions, events + enrollments, filtered search, pagination, tests, and delivery artifacts (README + Postman).
todos:
  - id: extract-constraints
    content: Confirm hard constraints from AGENTS.md and SPEC.md are reflected in the plan (default User only, signup/login rules, OTP gating, error/pagination shapes, required models, services/permissions/test discipline).
    status: in_progress
  - id: design-stack-structure
    content: Pick Django/DRF/JWT/Postgres versions and define project/app/module structure aligned with thin views + services + permission classes.
    status: pending
  - id: define-data-model
    content: Specify models, fields, indexes, validations, and DB-level unique constraint for active enrollments.
    status: pending
  - id: define-authz-api
    content: Specify auth flow, permissions, endpoints, and filtering/pagination behavior per spec.
    status: pending
  - id: test-artifacts-phases
    content: Enumerate test suite coverage, required docs/artifacts, and phased execution with commands after each phase.
    status: pending
isProject: false
---

# Django Events Backend Implementation Plan

## Hard constraints (must hold)
- **Default `auth.User` only** (no custom/swapped user model). Source: `[c:\OCA\Backend Task\AGENTS.md](c:\OCA\Backend Task\AGENTS.md)`
- **Signup payload only**: `email`, `password`, `role` (role ∈ `seeker|facilitator`). No username in requests/responses. Set `User.username = normalized_email` internally. Source: `[c:\OCA\Backend Task\AGENTS.md](c:\OCA\Backend Task\AGENTS.md)`, `[c:\OCA\Backend Task\SPEC.md](c:\OCA\Backend Task\SPEC.md)`
- **Login uses email+password**, but **unverified users cannot log in** (OTP verification required). Source: same
- **Stack**: Django + DRF + JWT + PostgreSQL. Source: `[c:\OCA\Backend Task\AGENTS.md](c:\OCA\Backend Task\AGENTS.md)`
- **Error shape** everywhere: `{ "detail": "message", "code": "error_code" }`. Source: same
- **Timezone-aware datetimes**, UTC-safe. Source: same
- **Architecture required**: `AccountProfile`, `EmailOTP` (hashed code, expiry, attempts, resend metadata), `Event`, `Enrollment(status=enrolled|canceled)` with **DB-level one active enrollment per seeker/event**. Source: `[c:\OCA\Backend Task\AGENTS.md](c:\OCA\Backend Task\AGENTS.md)`
- **Engineering rules**: thin views, business logic in services, checks in permission classes, tests for every behavior change, run migrations+tests+lint each phase, update README + Postman whenever API behavior changes. Source: `[c:\OCA\Backend Task\AGENTS.md](c:\OCA\Backend Task\AGENTS.md)`

## 1) Recommended stack and versions
- **Python**: 3.12.x
- **Django**: 5.1.x
- **Django REST Framework**: 3.15.x
- **JWT**: `djangorestframework-simplejwt` 5.3.x
- **PostgreSQL**: 16.x
- **Filtering**: `django-filter` 24.x
- **Testing**: `pytest` 8.x, `pytest-django` 4.9+, `factory_boy` 3.3+ (optional but recommended)
- **Lint/format**: `ruff` 0.6+ (lint+format) (or `black`+`isort` if ruff-format isn’t desired)
- **API docs (optional)**: `drf-spectacular` 0.27+ (if allowed; otherwise rely on README + Postman)
- **Bonus (optional)**: Docker + `celery` + `redis` (or `django-q`/`apscheduler`) for scheduled emails

## 2) Project structure (recommended)
- `manage.py`
- `config/`
  - `settings.py` (split settings modules if desired)
  - `urls.py`
  - `wsgi.py` / `asgi.py`
- `apps/`
  - `accounts/` (signup, OTP, login gating)
  - `events/` (event CRUD + search)
  - `enrollments/` (enroll/cancel + past/upcoming)
  - `common/` (shared errors, pagination, base models, utilities)
- `tests/` (pytest-style, or per-app tests)
- `postman/EventsPlatform.postman_collection.json`
- `README.md`
- Optional: `docker/`, `compose.yml`

## 3) Apps/modules to create
- **`accounts`**
  - serializers: signup, otp request/verify, login
  - services: user creation, OTP lifecycle, verification
  - permissions: role helpers (if shared, keep in `common`)
- **`events`**
  - services: create/update/delete with ownership checks (also guarded by permissions)
  - filters: search filters
- **`enrollments`**
  - services: enroll/cancel, list past/upcoming
- **`common`**
  - error handling (exception handler that returns `{detail, code}`)
  - pagination class (count/next/previous/results)
  - base model mixins (timestamps)
  - constants/enums

## 4) Models (fields + constraints)
### `AccountProfile` (one-to-one with `auth.User`)
- `user` (OneToOne, `User`)
- `role` (CharField, choices: `seeker`, `facilitator`, indexed)
- `email_verified` (BooleanField, default False)
- Optional: `created_at`, `updated_at`
- **Invariant**: `user.email` present; `user.username == normalized_email`.

### `EmailOTP`
- `user` (FK `User`, indexed)
- `purpose` (CharField) (at minimum: `email_verification`)
- `code_hash` (CharField) (store hashed OTP)
- `expires_at` (DateTimeField, indexed)
- `attempt_count` (SmallIntegerField)
- `max_attempts` (SmallIntegerField)
- `last_sent_at` (DateTimeField, null)
- `resend_count` (SmallIntegerField)
- `next_resend_at` (DateTimeField, null)
- `consumed_at` (DateTimeField, null)
- **Rules**:
  - OTP valid only before `expires_at` and if not consumed.
  - Attempt limit enforced (lockout until new OTP issued).
  - Resend throttling via `next_resend_at` and `resend_count`.

### `Event`
- `owner` (FK `User` as facilitator, indexed)
- `title` (CharField)
- `description` (TextField)
- `starts_at` (DateTimeField, indexed)
- `ends_at` (DateTimeField)
- `location` (CharField, optional)
- `capacity` (PositiveIntegerField)
- `is_published` (BooleanField default True or per spec needs)
- `created_at`, `updated_at`
- **Validation**: `ends_at > starts_at`, capacity > 0.
- **Indexes**: `(starts_at)`, `(owner, starts_at)`.

### `Enrollment`
- `event` (FK `Event`, indexed)
- `seeker` (FK `User`, indexed)
- `status` (choices: `enrolled`, `canceled`, indexed)
- `created_at`, `updated_at`
- **DB constraint**: one *active* enrollment per `(seeker, event)`.
  - Implement as a **partial unique constraint** on `(seeker_id, event_id)` where `status='enrolled'`.
- **Capacity enforcement**: only allow enroll if active enrolled count < capacity.

## 5) Auth flow
### Signup
- `POST /api/auth/signup/`
  - Input: `{email, password, role}` only.
  - Normalize email (lowercase, trim) and set:
    - `User.email = normalized_email`
    - `User.username = normalized_email` (internal only)
  - Create `AccountProfile(role=..., email_verified=False)`
  - Issue OTP for verification (create `EmailOTP` row; send email can be stubbed or console backend if allowed).
  - Response: do **not** include username.

### OTP verification
- `POST /api/auth/otp/request/` (resend)
  - Input: `{email}`
  - Enforce resend throttling and create/refresh OTP as per rules.
- `POST /api/auth/otp/verify/`
  - Input: `{email, code}`
  - Verify hash, expiry, attempts; on success set `AccountProfile.email_verified=True` and mark OTP consumed.

### Login (JWT)
- `POST /api/auth/login/`
  - Input: `{email, password}`
  - Authenticate against `User` (using `username=email` internally) and then **reject if `email_verified=False`** with `{detail, code}`.
  - Return access+refresh tokens.
- `POST /api/auth/token/refresh/`

## 6) Permissions
- **Global**: all protected endpoints require JWT.
- **Role-based**:
  - `IsSeeker`: profile role is `seeker`
  - `IsFacilitator`: profile role is `facilitator`
- **Ownership**:
  - `IsEventOwner`: facilitator owns the `Event.owner`
- **Enrollment rules**:
  - Only seekers can enroll/cancel.
  - Seekers can only view their own enrollments.
  - Facilitators can only CRUD their own events.

## 7) Endpoints (minimum required)
### Auth
- `POST /api/auth/signup/`
- `POST /api/auth/otp/request/`
- `POST /api/auth/otp/verify/`
- `POST /api/auth/login/`
- `POST /api/auth/token/refresh/`

### Events
- `GET /api/events/` (public or authenticated; choose authenticated if safer)
  - Filtered search (see below) + pagination
- `GET /api/events/{id}/`
- Facilitator only:
  - `POST /api/events/`
  - `PATCH /api/events/{id}/`
  - `DELETE /api/events/{id}/`
  - `GET /api/facilitator/events/` (list my events + counts)
    - counts: enrolled_count (active), canceled_count (optional), capacity, remaining_capacity

### Enrollments
- Seeker only:
  - `POST /api/events/{id}/enroll/`
  - `POST /api/events/{id}/cancel/` (or `DELETE /api/enrollments/{id}/` if you prefer; keep simple)
  - `GET /api/me/enrollments/past/`
  - `GET /api/me/enrollments/upcoming/`

## 8) Filters and pagination
- **Pagination**: DRF `PageNumberPagination` with exact shape: `count/next/previous/results`. (Acceptance check.) Source: `[c:\OCA\Backend Task\SPEC.md](c:\OCA\Backend Task\SPEC.md)`
- **Event search filters** (via `django-filter`):
  - `starts_at__gte`, `starts_at__lte` (or `date_from`, `date_to`)
  - `q` search over title/description (DRF SearchFilter or custom filter)
  - `facilitator_id` (owner)
  - `upcoming=true` shortcut (starts_at >= now)
  - ordering by `starts_at`
- **Enrollment listing**:
  - Past: events with `ends_at < now` (or `starts_at < now` depending spec interpretation)
  - Upcoming: `starts_at >= now`

## 9) Tests to write (must cover acceptance checks)
- **Signup**
  - Creates `User` with `username == normalized_email` but does not expose username
  - Creates `AccountProfile` with correct role, `email_verified=False`
  - Invalid role rejected
- **OTP**
  - Verify success sets `email_verified=True` and consumes OTP
  - Expired OTP rejected
  - Attempt limit enforced (wrong code increments attempts; lock out)
  - Resend throttling enforced
- **Login/JWT**
  - Unverified users cannot log in (error `{detail, code}`)
  - Verified users can obtain tokens with email+password
- **Events**
  - Facilitator can CRUD own events
  - Facilitator cannot modify others’ events
  - Seeker cannot create/update/delete events
  - Filtering + pagination correctness
- **Enrollments**
  - Seeker can enroll if capacity available
  - Capacity enforced (reject when full)
  - Duplicate active enrollment blocked (DB constraint + service-level error)
  - Cancel changes status to `canceled` and allows re-enroll
  - Past/upcoming endpoints return correct partition
- **Error shape**
  - Representative failures return `{detail, code}` consistently

## 10) Docs/artifacts to produce
- `[c:\OCA\Backend Task\README.md](c:\OCA\Backend Task\README.md)`
  - Setup (env, DB), run, test, lint
  - Auth flow steps (signup → OTP verify → login)
  - Endpoint list + examples
  - Pagination + error shape guarantees
- `postman/EventsPlatform.postman_collection.json`
  - Requests for all endpoints
  - Environment variables for base_url, access_token, refresh_token
  - Example payloads and happy-path flows
- Optional (bonus): `compose.yml` + Docker docs; background job explanation for scheduled emails

## 11) Exact phases of execution
### Phase A — Foundation/scaffold
- Create/verify virtualenv, install dependencies.
- Create Django project + apps skeleton (`accounts`, `events`, `enrollments`, `common`).
- Configure settings: PostgreSQL, DRF, JWT, timezone/UTC.
- Add global exception handler enforcing `{detail, code}` and default pagination enforcing `count/next/previous/results`.
- Establish engineering layout: thin views, service layer modules, permission classes modules.

### Phase B — Auth + OTP
- Implement `AccountProfile` and `EmailOTP`.
- Implement signup: accepts **only** `email,password,role`; sets `User.username = normalized_email` internally; creates profile with `email_verified=False`.
- Implement OTP request/resend with throttling metadata.
- Implement OTP verify with hashed code, expiry, attempt limit, consume-on-success; sets `email_verified=True`.
- Implement login (email+password) and refresh with **verification gate** (unverified users cannot log in).

### Phase C — Models + constraints
- Implement `Event`.
- Implement `Enrollment(status=enrolled|canceled)`.
- Add **DB-level partial unique constraint** for one active enrollment per (seeker,event).
- Add useful DB indexes (starts_at, owner+starts_at, seeker/event/status) and validations (`ends_at > starts_at`, capacity > 0).
- Implement service-layer invariants for capacity enforcement and consistent `{detail, code}` errors for constraint violations.

### Phase D — Seeker endpoints
- Event discovery endpoints (list/detail) with filters + pagination.
- Enrollment endpoints for seekers: enroll, cancel, list past, list upcoming.
- Permission enforcement: seeker-only, self-only access.
- Ensure acceptance checks: duplicate active enrollment blocked; capacity enforced; pagination shape correct.

### Phase E — Facilitator endpoints
- Facilitator CRUD for own events.
- Facilitator list “my events” with counts (active enrolled count; optionally canceled count; remaining capacity).
- Permission/ownership enforcement: facilitators only; cannot touch others’ events.

### Phase F — Tests
- Implement the test suite covering all behaviors in section 9, with explicit tests for acceptance checks and error shape.
- Ensure migrations are valid and tests are green.
- Run lint/format checks.

### Phase G — README + Postman
- Complete README with setup, env vars, auth flow, endpoint catalog, error/pagination contract.
- Build a complete Postman collection covering happy paths and key failure cases.
- Re-run tests + lint to ensure artifacts match behavior.

### Phase H — Bonus
- Optional dockerization (Dockerfile + compose + docs).
- Optional scheduled mail implementation plan (or implementation, if time) for follow-up/reminder emails.

## 12) Commands to run after each phase
> Commands assume Windows PowerShell; adjust paths as needed.

### After Phase A (foundation/scaffold)
- `python -m venv .venv`
- `.\.venv\Scripts\Activate.ps1`
- `python -m pip install --upgrade pip`
- `pip install -r requirements.txt`
- Confirm DB reachable; set `DATABASE_URL`/env vars.
- `python manage.py makemigrations`
- `python manage.py migrate`
- `python manage.py runserver`

### After Phase B (auth + OTP)
- `python manage.py makemigrations`
- `python manage.py migrate`
- `pytest -q`
- `ruff check .` (and `ruff format .` if used)

### After Phase C (models + constraints)
- `python manage.py makemigrations`
- `python manage.py migrate`
- `pytest -q`
- `ruff check .`

### After Phase D (seeker endpoints)
- `python manage.py makemigrations`
- `python manage.py migrate`
- `pytest -q`
- `ruff check .`

### After Phase E (facilitator endpoints)
- `python manage.py makemigrations`
- `python manage.py migrate`
- `pytest -q`
- `ruff check .`

### After Phase F (tests)
- `pytest -q`
- `ruff check .`
- `python manage.py check`

### After Phase G (README + Postman)
- Validate Postman collection runs end-to-end.
- Final: `pytest -q` and `ruff check .`

### After Phase H (bonus)
- If dockerized: `docker compose build` then `docker compose up`
- If scheduled mail added: run the worker/scheduler command(s) chosen and verify email events fire at the right times.
