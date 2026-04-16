from __future__ import annotations

from django.urls import path

from events.views import (
    EventDetailView,
    EventEnrollView,
    EventListView,
    SeekerEnrollmentCancelView,
    SeekerEnrollmentPastListView,
    SeekerEnrollmentUpcomingListView,
)

urlpatterns = [
    path("events/", EventListView.as_view(), name="event-list"),
    path("events/<int:pk>/enroll/", EventEnrollView.as_view(), name="event-enroll"),
    path("events/<int:pk>/", EventDetailView.as_view(), name="event-detail"),
    path(
        "me/enrollments/upcoming/",
        SeekerEnrollmentUpcomingListView.as_view(),
        name="seeker-enrollments-upcoming",
    ),
    path(
        "me/enrollments/past/",
        SeekerEnrollmentPastListView.as_view(),
        name="seeker-enrollments-past",
    ),
    path(
        "me/enrollments/<int:pk>/cancel/",
        SeekerEnrollmentCancelView.as_view(),
        name="seeker-enrollment-cancel",
    ),
]
