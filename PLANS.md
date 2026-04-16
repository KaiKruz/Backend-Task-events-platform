# PLANS.md

## Current planning source
Detailed working plans are stored in:
- `.cursor/plans/django-events-backend_655eb26c.plan.md`
- `.cursor/plans/django-events-backend-phase1_6f286ef0.plan.md`

## Current status
Phases 1–3 are complete and validation is green (scaffold, auth + OTP, events + enrollments models/services/tests).

## Current repo structure
- config/
- core/
- accounts/
- events/
- tests/
- requirements/

## Phase sequence
1. Phase 1 — Scaffold ✅
2. Phase 2 — Auth + OTP ✅
3. Phase 3 — Events + Enrollments ✅
4. Phase 4 — Seeker features
5. Phase 5 — Facilitator features
6. Phase 6 — Docs + polish
7. Phase 7 — Bonus

## Next phase
Phase 4 — Seeker features

Scope (see detailed plan under `.cursor/plans/`):
- Seeker-facing API for discovery, enrollment, and enrollment history (builds on Phase 3 models and services).

## Non-negotiables
- Use Django default User only
- No username in signup payloads
- Unverified users cannot log in
- Keep views thin
- Add tests for each behavior change
- Do not start bonus work before core is complete
