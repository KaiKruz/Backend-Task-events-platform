# Assignment Spec

## Core requirements
- [ ] Django backend for events platform
- [ ] Default Django User model only
- [ ] Signup accepts email, password, role
- [ ] No username field in signup request
- [ ] Email OTP verification before login
- [ ] OTP expiry and attempt limits
- [ ] JWT login and refresh
- [ ] Roles: seeker, facilitator
- [ ] Role and ownership enforcement
- [ ] Event model
- [ ] Enrollment model
- [ ] Filtered event search
- [ ] Seeker enroll in event
- [ ] Past enrollments
- [ ] Upcoming enrollments
- [ ] Facilitator CRUD for own events
- [ ] Facilitator list my events with counts
- [ ] PostgreSQL migrations
- [ ] Useful DB indexes
- [ ] README
- [ ] Postman collection

## Bonus
- [ ] Dockerized project
- [ ] Scheduled mail
- [ ] Follow-up email 1 hour after enrollment
- [ ] Reminder email 1 hour before event start
- [ ] Public deployment URL

## Acceptance checks
- [ ] Unverified users cannot log in
- [ ] Duplicate active enrollment blocked
- [ ] Capacity enforced
- [ ] Pagination shape is count/next/previous/results
- [ ] Error shape is detail/code
