import django_filters
from .models import Transfer


class TransferFilterSet(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='审批状态')
    fromBranch = django_filters.CharFilter(field_name='调出分公司')
    toBranch = django_filters.CharFilter(field_name='调入分公司')
    type = django_filters.CharFilter(field_name='action_type')
    keyword = django_filters.CharFilter(method='filter_keyword')

    ordering = django_filters.OrderingFilter(fields=(
        ('调拨日期', '调拨日期'),
        ('created_at', 'created_at'),
    ))

    class Meta:
        model = Transfer
        fields = []

    def filter_keyword(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(资产名称__icontains=value)
            | Q(资产编号__icontains=value)
            | Q(调出分公司__icontains=value)
            | Q(调入分公司__icontains=value)
        )
