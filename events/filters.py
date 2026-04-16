from __future__ import annotations

from django.db.models import Q
from django_filters import rest_framework as filters

from events.models import Event


class EventFilter(filters.FilterSet):
    location = filters.CharFilter(field_name="location", lookup_expr="iexact")
    language = filters.CharFilter(field_name="language", lookup_expr="iexact")
    starts_after = filters.IsoDateTimeFilter(field_name="starts_at", lookup_expr="gte")
    starts_before = filters.IsoDateTimeFilter(field_name="starts_at", lookup_expr="lte")
    q = filters.CharFilter(method="filter_q")

    class Meta:
        model = Event
        fields = ["location", "language", "starts_after", "starts_before", "q"]

    def filter_q(self, queryset, name, value):
        if not value:
            return queryset
        term = value.strip()
        if not term:
            return queryset
        return queryset.filter(Q(title__icontains=term) | Q(description__icontains=term))
