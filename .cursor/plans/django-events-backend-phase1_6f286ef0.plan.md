---
name: django-events-backend-phase1
overview: Phase 1 creates a clean, professional Django + DRF + SimpleJWT + Postgres scaffold (settings split, apps, routing, error/pagination wiring, and dev tooling) without implementing business logic endpoints yet.
todos:
  - id: phase1-layout
    content: Decide and finalize repo layout (`config/`, `core/`, `accounts/`, `events/`, `requirements/`, `tests/`).
    status: pending
  - id: phase1-deps
    content: Add dependency and tooling files (`requirements/base.txt`, `requirements/dev.txt`, `pyproject.toml`, `pytest.ini`, `.env.example`, `.gitignore`).
    status: pending
  - id: phase1-django-scaffold
    content: Generate Django project/app scaffold and settings split; wire DRF + SimpleJWT + postgres env loading.
    status: pending
  - id: phase1-api-plumbing
    content: Implement exception handler + pagination classes and hook them into `REST_FRAMEWORK` settings.
    status: pending
  - id: phase1-routing
    content: Add clean URL routing under `/api/` with per-app `urls.py` and a health endpoint.
    status: pending
  - id: phase1-validation
    content: Run checks/migrations/tests/lint commands and document them in README.
    status: pending
isProject: false
---

## What I found in the repo
- Only assignment docs are present right now: `[README.md](c:\OCA\Backend Task\README.md)`, `[SPEC.md](c:\OCA\Backend Task\SPEC.md)`, `[AGENTS.md](c:\OCA\Backend Task\AGENTS.md)`.
- The requested dependency/config files are **not present yet** (no `requirements/`, no `pyproject.toml`, no `pytest.ini`, no `.env.example`), and there is **no Django project scaffold** yet (no `manage.py`, no `settings.py`).

## Phase 1 objectives (scaffold only)
- Create a Django project with **settings split** (base/local/production).
- Add DRF + SimpleJWT configuration (library installed and settings wired), including:
  - **Pagination**: `count/next/previous/results`
  - **Exception envelope**: `{ "detail": "message", "code": "error_code" }`
- Create initial Django apps and folders for the future phases (**folders only; no domain models, no auth flows, no OTP logic**).
- Prepare Postgres + env configuration and local dev ergonomics.
- Add test + lint toolchain and validation commands (keep tooling minimal: `ruff` + `pytest`).

## 1) Exact files to create or modify
### Create (new)
- **Project + apps**
  - `[manage.py](c:\OCA\Backend Task\manage.py)`
  - `[config/__init__.py](c:\OCA\Backend Task\config\__init__.py)`
  - `[config/asgi.py](c:\OCA\Backend Task\config\asgi.py)`
  - `[config/wsgi.py](c:\OCA\Backend Task\config\wsgi.py)`
  - `[config/urls.py](c:\OCA\Backend Task\config\urls.py)`
  - `[config/settings/__init__.py](c:\OCA\Backend Task\config\settings\__init__.py)`
  - `[config/settings/base.py](c:\OCA\Backend Task\config\settings\base.py)`
  - `[config/settings/local.py](c:\OCA\Backend Task\config\settings\local.py)`
  - `[config/settings/production.py](c:\OCA\Backend Task\config\settings\production.py)`
  - `[config/settings/logging.py](c:\OCA\Backend Task\config\settings\logging.py)` (optional but recommended for clean separation)

- **Core/common utilities (wiring only)**
  - `[core/__init__.py](c:\OCA\Backend Task\core\__init__.py)`
  - `[core/apps.py](c:\OCA\Backend Task\core\apps.py)`
  - `[core/api/__init__.py](c:\OCA\Backend Task\core\api\__init__.py)`
  - `[core/api/exceptions.py](c:\OCA\Backend Task\core\api\exceptions.py)` (custom DRF exception handler)
  - `[core/api/pagination.py](c:\OCA\Backend Task\core\api\pagination.py)`
  - `[core/api/renderers.py](c:\OCA\Backend Task\core\api\renderers.py)` (optional: enforce consistent output)
  - `[core/health/__init__.py](c:\OCA\Backend Task\core\health\__init__.py)`
  - `[core/health/views.py](c:\OCA\Backend Task\core\health\views.py)` (simple health endpoint)
  - `[core/health/urls.py](c:\OCA\Backend Task\core\health\urls.py)`

- **Domain apps (folders only; no domain models in Phase 1)**
  - `[accounts/__init__.py](c:\OCA\Backend Task\accounts\__init__.py)`
  - `[accounts/apps.py](c:\OCA\Backend Task\accounts\apps.py)`
  - `[accounts/models.py](c:\OCA\Backend Task\accounts\models.py)` (empty placeholder; models start Phase 2)
  - `[accounts/admin.py](c:\OCA\Backend Task\accounts\admin.py)` (empty placeholder)
  - `[accounts/migrations/__init__.py](c:\OCA\Backend Task\accounts\migrations\__init__.py)`
  - `[events/__init__.py](c:\OCA\Backend Task\events\__init__.py)`
  - `[events/apps.py](c:\OCA\Backend Task\events\apps.py)`
  - `[events/models.py](c:\OCA\Backend Task\events\models.py)` (empty placeholder; models start Phase 2)
  - `[events/admin.py](c:\OCA\Backend Task\events\admin.py)` (empty placeholder)
  - `[events/migrations/__init__.py](c:\OCA\Backend Task\events\migrations\__init__.py)`

- **Tests scaffold**
  - `[tests/__init__.py](c:\OCA\Backend Task\tests\__init__.py)`
  - `[tests/test_health.py](c:\OCA\Backend Task\tests\test_health.py)`
  - `[tests/test_error_envelope.py](c:\OCA\Backend Task\tests\test_error_envelope.py)`
  - `[tests/test_pagination_shape.py](c:\OCA\Backend Task\tests\test_pagination_shape.py)`

- **Dependency/tooling/config**
  - `[requirements/base.txt](c:\OCA\Backend Task\requirements\base.txt)`
  - `[requirements/dev.txt](c:\OCA\Backend Task\requirements\dev.txt)`
  - `[pyproject.toml](c:\OCA\Backend Task\pyproject.toml)` (ruff + pytest config)
  - `[pytest.ini](c:\OCA\Backend Task\pytest.ini)` (or configure fully in `pyproject.toml`, but you asked for `pytest.ini`)
  - `[.env.example](c:\OCA\Backend Task\.env.example)`
  - `[.gitignore](c:\OCA\Backend Task\.gitignore)`

### Modify (existing)
- `[README.md](c:\OCA\Backend Task\README.md)`
  - Add local setup steps (venv, install, env vars, Postgres, runserver, tests/lint).

## 2) Recommended directory structure
- Keep a standard, review-friendly layout (no cleverness):

```text
c:\OCA\Backend Task\
  config/
    settings/
      base.py
      local.py
      production.py
      logging.py
    urls.py
    asgi.py
    wsgi.py
  core/
    api/
      exceptions.py
      pagination.py
      renderers.py
    health/
      urls.py
      views.py
  accounts/
    migrations/
    admin.py
    apps.py
    models.py
  events/
    migrations/
    admin.py
    apps.py
    models.py
  tests/
  requirements/
    base.txt
    dev.txt
  manage.py
  pyproject.toml
  pytest.ini
  .env.example
  README.md
```

Rationale:
- `config/` holds the Django project (settings/urls/wsgi/asgi).
- `core/` holds shared API plumbing (exception/pagination/health).
- `accounts/` and `events/` are domain apps aligned to SPEC.

## 3) Package installation steps (Windows/PowerShell friendly)
- Create venv:
  - `py -m venv .venv`
  - `./.venv/Scripts/Activate.ps1`
- Upgrade installer tooling:
  - `python -m pip install -U pip wheel`
- Install dependencies:
  - `pip install -r requirements\dev.txt`

## 4) Django project/app scaffold plan
- Create project:
  - `django-admin startproject config .`
- Create apps:
  - `python manage.py startapp core`
  - `python manage.py startapp accounts`
  - `python manage.py startapp events`
- Move to settings split:
  - Create `config/settings/` package.
  - Update `manage.py`, `asgi.py`, `wsgi.py` to point to `config.settings.local` by default for dev.

Non-negotiables satisfied by design:
- No custom user model.
- Phase 1 does **not** add any auth endpoints that would accidentally require/expose `username`.

## 5) Settings split plan (base/local/production)
- `base.py`
  - `INSTALLED_APPS`: Django + `rest_framework` + `rest_framework_simplejwt` (+ optionally `django_filters`) + local apps.
  - `MIDDLEWARE`: standard.
  - `AUTH_PASSWORD_VALIDATORS`: keep defaults.
  - `LANGUAGE_CODE`, `TIME_ZONE='UTC'`, `USE_TZ=True`.
  - `REST_FRAMEWORK` defaults (auth, exception handler, pagination).
  - `SIMPLE_JWT` defaults.
  - `DATABASES` from env.
  - `DEFAULT_AUTO_FIELD`.
- `local.py`
  - `DEBUG=True`
  - permissive CORS (only if needed; otherwise skip)
  - console logging
- `production.py`
  - `DEBUG=False`
  - secure cookie/SSL headers (documented; actual infra may be Phase later)
  - allowed hosts from env

Env loading approach (Phase 1):
- Prefer `django-environ` to load `.env` reliably on Windows.

## 6) DRF configuration plan
In `config/settings/base.py`:
- Set `DEFAULT_AUTHENTICATION_CLASSES` to JWT auth.
- Set `DEFAULT_PERMISSION_CLASSES` to authenticated-by-default or allow-by-default depending on endpoint strategy:
  - Recommended: `IsAuthenticated` globally, then explicitly open `health/` (Phase 1 only).
- Set `DEFAULT_PAGINATION_CLASS` to a custom `PageNumberPagination` subclass in `core/api/pagination.py`.
- Set `PAGE_SIZE` (e.g., 10/20) in settings.
- Add `DEFAULT_EXCEPTION_HANDLER` pointing to `core.api.exceptions.drf_exception_handler`.

## 7) SimpleJWT configuration plan
In `config/settings/base.py`:
- Configure token lifetimes appropriate for assignment review (e.g., access 5–15 min, refresh 1–7 days).
- Enable rotation/blacklist only if you include `rest_framework_simplejwt.token_blacklist` (optional Phase 2; can be planned now).
- Phase 1 explicitly **does not** expose token obtain/login endpoints yet, to avoid any accidental `username` payload requirements. Phase 2 will add email-based login + verification gating per SPEC.

## 8) Database/env configuration plan
- Use PostgreSQL in all environments.
- `.env.example` includes:
  - `DJANGO_SETTINGS_MODULE=config.settings.local`
  - `DJANGO_SECRET_KEY=...`
  - `DJANGO_DEBUG=1`
  - `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`
  - `DATABASE_URL=postgres://user:pass@localhost:5432/events_db`
  - `JWT_*` optional overrides
- In `base.py`:
  - Parse `DATABASE_URL` and fall back to explicit `DB_HOST/DB_PORT/...` if needed.

## 9) Exception handler and pagination wiring plan
- `core/api/exceptions.py`
  - Wrap DRF default exception handler.
  - For validation errors and DRF APIException, normalize output into:
    - `{ "detail": "...", "code": "..." }`
  - For field errors, keep a predictable approach:
    - Option A (recommended): keep DRF’s field error structure under `detail` as object/string, but always include `code`.
- `core/api/pagination.py`
  - Subclass `PageNumberPagination` to guarantee shape `count/next/previous/results`.
  - Set `page_size_query_param` optionally (or keep fixed).

## 10) URL routing plan
- `config/urls.py`
  - Mount under `/api/`.
  - Include:
    - `/api/health/`
- Defer `/api/auth/` and `/api/events/` wiring until Phase 2+ when endpoints exist.
- Per-app `urls.py` to keep `config/urls.py` clean.

Suggested routing skeleton:
- `core.health.urls`: `GET /api/health/`

## 11) Validation commands to run (Phase 1)
- **Django**
  - `python manage.py check`
  - `python manage.py migrate`
  - `python manage.py runserver`
- **Tests**
  - `pytest`
- **Lint/format**
  - `ruff check .`
  - `ruff format .`

## 12) Likely risks / mistakes to avoid
- Accidentally creating a **custom user model** (`AUTH_USER_MODEL`) — prohibited.
- Accidentally exposing `username` in serializer fields or docs.
- Using JWT login that authenticates via `username` by default — Phase 2 must ensure authentication is by **email** and blocks `email_verified=False`.
- Inconsistent error response shapes (DRF defaults vary); central exception handler is essential early.
- Timezone bugs: always `USE_TZ=True`, store UTC, be careful with naive datetimes.
- Enrollment uniqueness: needs a **DB-level constraint** (partial unique index) for “one active enrollment” — plan it early because it affects migrations and query patterns.
- Settings split drift: keep environment-specific overrides minimal and leave defaults in `base.py`.
