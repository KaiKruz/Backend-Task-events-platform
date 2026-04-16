from __future__ import annotations

from django.db.models import Case, Count, IntegerField, Q, When
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
from events.permissions import IsEventOwner, IsVerifiedFacilitator, IsVerifiedSeeker
from events.serializers import (
    EmptyPayloadSerializer,
    EventSerializer,
    FacilitatorEventSummarySerializer,
    FacilitatorEventWriteSerializer,
    SeekerEnrollmentSerializer,
)
from events.services import (
    cancel_enrollment,
    create_event,
    delete_event,
    enroll_seeker,
    update_event,
)


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


class FacilitatorEventListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsVerifiedFacilitator]

    def get_queryset(self):
        return Event.objects.filter(created_by=self.request.user).order_by("starts_at", "id")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return FacilitatorEventWriteSerializer
        return EventSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = create_event(created_by=request.user, **serializer.validated_data)
        return Response(EventSerializer(event).data, status=status.HTTP_201_CREATED)


class FacilitatorEventDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsVerifiedFacilitator, IsEventOwner]
    queryset = Event.objects.all()

    def get_queryset(self):
        return Event.objects.filter(created_by=self.request.user)

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return FacilitatorEventWriteSerializer
        return EventSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        event = self.get_object()
        serializer = self.get_serializer(event, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_event = update_event(event=event, **serializer.validated_data)
        return Response(EventSerializer(updated_event).data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        event = self.get_object()
        delete_event(event=event, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FacilitatorMySummaryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsVerifiedFacilitator]
    serializer_class = FacilitatorEventSummarySerializer

    def get_queryset(self):
        return (
            Event.objects.filter(created_by=self.request.user)
            .annotate(
                total_active_enrollments=Count(
                    "enrollments",
                    filter=Q(enrollments__status=EnrollmentStatus.ENROLLED),
                ),
            )
            .order_by("starts_at", "id")
        )
