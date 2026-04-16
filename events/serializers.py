from __future__ import annotations

from rest_framework import serializers

from events.models import Enrollment, Event


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "language",
            "location",
            "starts_at",
            "ends_at",
            "capacity",
        ]


class FacilitatorEventWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(allow_blank=True, required=False, default="")
    language = serializers.CharField(max_length=64)
    location = serializers.CharField(max_length=255)
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    capacity = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class FacilitatorEventSummarySerializer(serializers.ModelSerializer):
    total_active_enrollments = serializers.IntegerField(read_only=True)
    available_seats = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "starts_at",
            "ends_at",
            "capacity",
            "total_active_enrollments",
            "available_seats",
        ]

    def get_available_seats(self, obj):
        if obj.capacity is None:
            return None
        remaining = obj.capacity - int(getattr(obj, "total_active_enrollments", 0) or 0)
        return max(remaining, 0)


class SeekerEnrollmentSerializer(serializers.ModelSerializer):
    event = EventSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "status", "created_at", "updated_at", "event"]


class EmptyPayloadSerializer(serializers.Serializer):
    """Validates optional empty JSON bodies for POST actions."""

    pass
