import django_filters
from django_filters import BaseInFilter, CharFilter
from .models import InventoryTask


class StatusInFilter(BaseInFilter, CharFilter):
    pass


class BranchIdInFilter(BaseInFilter, CharFilter):
    """分公司多选（逗号分隔 id → __in 并集）。"""


class InventoryTaskFilterSet(django_filters.FilterSet):
    status = StatusInFilter(field_name='status', lookup_expr='in')
    branchId = BranchIdInFilter(field_name='branch_id', lookup_expr='in')

    ordering = django_filters.OrderingFilter(fields=(
        ('created_at', 'created_at'),
        ('started_at', 'started_at'),
    ))

    class Meta:
        model = InventoryTask
        fields = []
