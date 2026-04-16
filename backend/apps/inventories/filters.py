import django_filters
from django_filters import BaseInFilter, CharFilter
from .models import InventoryTask


class StatusInFilter(BaseInFilter, CharFilter):
    pass


class InventoryTaskFilterSet(django_filters.FilterSet):
    status = StatusInFilter(field_name='status', lookup_expr='in')
    branchId = django_filters.CharFilter(field_name='branch_id')

    ordering = django_filters.OrderingFilter(fields=(
        ('created_at', 'created_at'),
        ('started_at', 'started_at'),
    ))

    class Meta:
        model = InventoryTask
        fields = []
