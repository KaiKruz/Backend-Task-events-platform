# Events Backend Assignment

## Goal
Build a submission-quality Django REST API for the Events Platform assignment.

## Hard constraints
- Use Django's default auth.User only. Do NOT swap the user model.
- Signup accepts only: email, password, role.
- Do NOT expose or require username in API payloads.
- Internally set username from normalized email.
- Login must use email + password.
- Unverified users must not be able to log in.
- Roles are only: seeker, facilitator.
- Use Django + DRF + JWT + PostgreSQL.
- Return errors as: { "detail": "message", "code": "error_code" }.
- Keep datetimes timezone-aware and UTC-safe.

## Required architecture
- Keep built-in User.
- Add AccountProfile with role and email_verified.
- Add EmailOTP with hashed code, expiry, attempts, and resend metadata.
- Add Event.
- Add Enrollment with status=enrolled|canceled.
- Enforce one active enrollment per seeker/event at the DB level.

## Engineering rules
- Plan first before code changes.
- List files to change before editing.
- Keep views thin.
- Put business logic in services.
- Put auth/role/ownership checks in permission classes.
- Add or update tests for every behavior change.
- Run migrations, tests, and lint before claiming a phase is done.
- Update README and Postman collection when API behavior changes.

## Done means
- Spec is satisfied exactly
- Tests pass
- Migrations are valid
- README is complete
- Postman collection is complete
- No required feature is left as TODO
