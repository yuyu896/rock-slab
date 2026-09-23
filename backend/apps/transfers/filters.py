import django_filters
from django.db.models import Q
from django_filters import BaseInFilter, CharFilter
from .models import Transfer


class BranchNameInFilter(BaseInFilter, CharFilter):
    """分公司多选（逗号分隔名称 → __in 并集）。"""


class TransferFilterSet(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='审批状态')
    fromBranch = BranchNameInFilter(field_name='调出分公司', lookup_expr='in')
    toBranch = BranchNameInFilter(field_name='调入分公司', lookup_expr='in')
    type = django_filters.CharFilter(field_name='action_type')
    docNumber = django_filters.CharFilter(field_name='单据编号')
    assetCode = django_filters.CharFilter(method='filter_asset_code')
    keyword = django_filters.CharFilter(method='filter_keyword')

    ordering = django_filters.OrderingFilter(fields=(
        ('调拨日期', '调拨日期'),
        ('created_at', 'created_at'),
    ))

    class Meta:
        model = Transfer
        fields = []

    def filter_asset_code(self, queryset, name, value):
        return queryset.filter(lines__item__asset_code__icontains=value).distinct()

    def filter_keyword(self, queryset, name, value):
        return queryset.filter(
            Q(单据编号__icontains=value)
            | Q(lines__item__asset_name__icontains=value)
            | Q(lines__item__asset_code__icontains=value)
            | Q(调出分公司__icontains=value)
            | Q(调入分公司__icontains=value)
            | Q(经办人__icontains=value)
            | Q(创建人__icontains=value)
        ).distinct()
