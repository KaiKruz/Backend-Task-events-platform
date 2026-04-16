from django.contrib import admin

from .models import Enrollment, Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "language",
        "location",
        "starts_at",
        "ends_at",
        "capacity",
        "created_by",
        "created_at",
    )
    list_filter = ("language",)
    search_fields = ("title", "description", "location")
    raw_id_fields = ("created_by",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("id", "event", "seeker", "status", "created_at", "updated_at")
    list_filter = ("status",)
    raw_id_fields = ("event", "seeker")
