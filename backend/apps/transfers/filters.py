import django_filters
from .models import Transfer


class TransferFilterSet(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='审批状态')
    fromBranch = django_filters.CharFilter(field_name='调出分公司')
    toBranch = django_filters.CharFilter(field_name='调入分公司')
    type = django_filters.CharFilter(field_name='action_type')

    ordering = django_filters.OrderingFilter(fields=(
        ('调拨日期', '调拨日期'),
        ('created_at', 'created_at'),
    ))

    class Meta:
        model = Transfer
        fields = []
