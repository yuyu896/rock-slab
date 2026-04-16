import django_filters as df
from django.db.models import Q
from .models import AuditLog


class AuditLogFilterSet(df.FilterSet):
    """审计日志过滤器"""
    action = df.CharFilter(field_name='action')
    resource_type = df.CharFilter(field_name='resource_type')
    user_id = df.UUIDFilter(field_name='user__id')
    is_success = df.BooleanFilter(field_name='is_success')
    start_date = df.DateFilter(field_name='created_at', lookup_expr='date__gte')
    end_date = df.DateFilter(field_name='created_at', lookup_expr='date__lte')
    search = df.CharFilter(method='filter_search')

    class Meta:
        model = AuditLog
        fields = []

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(user_name__icontains=value) |
            Q(resource_name__icontains=value) |
            Q(description__icontains=value)
        )
