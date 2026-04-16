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


class SeekerEnrollmentSerializer(serializers.ModelSerializer):
    event = EventSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "status", "created_at", "updated_at", "event"]


class EmptyPayloadSerializer(serializers.Serializer):
    """Validates optional empty JSON bodies for POST actions."""

    pass
