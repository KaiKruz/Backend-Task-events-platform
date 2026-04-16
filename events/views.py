from __future__ import annotations

from django.db.models import Case, IntegerField, When
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from events.filters import EventFilter
from events.models import Enrollment, EnrollmentStatus, Event
from events.permissions import IsVerifiedSeeker
from events.serializers import (
    EmptyPayloadSerializer,
    EventSerializer,
    SeekerEnrollmentSerializer,
)
from events.services import cancel_enrollment, enroll_seeker


class EventListView(generics.ListAPIView):
    serializer_class = EventSerializer
    permission_classes = [AllowAny]
    filterset_class = EventFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["starts_at", "title", "created_at", "id"]

    def get_queryset(self):
        now = timezone.now()
        return (
            Event.objects.annotate(
                _upcoming_first=Case(
                    When(starts_at__gte=now, then=0),
                    default=1,
                    output_field=IntegerField(),
                ),
            )
            .order_by("_upcoming_first", "starts_at")
        )


class EventDetailView(generics.RetrieveAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [AllowAny]


class EventEnrollView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedSeeker]

    def post(self, request, pk: int):
        serializer = EmptyPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = get_object_or_404(Event.objects.all(), pk=pk)
        enrollment = enroll_seeker(event=event, seeker=request.user)
        enrollment = Enrollment.objects.select_related("event").get(pk=enrollment.pk)
        return Response(
            SeekerEnrollmentSerializer(enrollment).data,
            status=status.HTTP_201_CREATED,
        )


class SeekerEnrollmentUpcomingListView(generics.ListAPIView):
    serializer_class = SeekerEnrollmentSerializer
    permission_classes = [IsAuthenticated, IsVerifiedSeeker]

    def get_queryset(self):
        now = timezone.now()
        return (
            Enrollment.objects.filter(
                seeker=self.request.user,
                status=EnrollmentStatus.ENROLLED,
                event__starts_at__gte=now,
            )
            .select_related("event")
            .order_by("event__starts_at", "id")
        )


class SeekerEnrollmentPastListView(generics.ListAPIView):
    serializer_class = SeekerEnrollmentSerializer
    permission_classes = [IsAuthenticated, IsVerifiedSeeker]

    def get_queryset(self):
        now = timezone.now()
        return (
            Enrollment.objects.filter(
                seeker=self.request.user,
                status=EnrollmentStatus.ENROLLED,
                event__starts_at__lt=now,
            )
            .select_related("event")
            .order_by("-event__starts_at", "-id")
        )


class SeekerEnrollmentCancelView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedSeeker]

    def post(self, request, pk: int):
        serializer = EmptyPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enrollment = get_object_or_404(
            Enrollment.objects.select_related("event"),
            pk=pk,
        )
        self.check_object_permissions(request, enrollment)
        updated = cancel_enrollment(enrollment=enrollment, seeker=request.user)
        return Response(
            SeekerEnrollmentSerializer(updated).data,
            status=status.HTTP_200_OK,
        )
