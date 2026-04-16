# Assignment Spec

## Core requirements
- [x] Django backend for events platform
- [x] Default Django User model only
- [x] Signup accepts email, password, role
- [x] No username field in signup request
- [x] Email OTP verification before login
- [x] OTP expiry and attempt limits
- [x] JWT login and refresh
- [x] Roles: seeker, facilitator
- [x] Role and ownership enforcement
- [x] Event model
- [x] Enrollment model
- [x] Filtered event search
- [x] Seeker enroll in event
- [x] Past enrollments
- [x] Upcoming enrollments
- [x] Facilitator CRUD for own events
- [x] Facilitator list my events with counts
- [x] PostgreSQL migrations
- [x] Useful DB indexes
- [x] README
- [x] Postman collection

## Bonus
- [ ] Dockerized project
- [ ] Scheduled mail
- [ ] Follow-up email 1 hour after enrollment
- [ ] Reminder email 1 hour before event start
- [ ] Public deployment URL

## Acceptance checks
- [x] Unverified users cannot log in
- [x] Duplicate active enrollment blocked
- [x] Capacity enforced
- [x] Pagination shape is count/next/previous/results
- [x] Error shape is detail/code
