import django_filters
from .models import User


class UserFilterSet(django_filters.FilterSet):
    role = django_filters.CharFilter(field_name='role')
    branch = django_filters.CharFilter(method='filter_branch')
    region = django_filters.CharFilter(field_name='region_id')
    team = django_filters.CharFilter(field_name='team_id')
    keyword = django_filters.CharFilter(method='filter_keyword')
    status = django_filters.CharFilter(field_name='status')

    ordering = django_filters.OrderingFilter(fields=(
        ('created_at', 'created_at'),
        ('name', 'name'),
    ))

    class Meta:
        model = User
        fields = []

    def filter_branch(self, queryset, name, value):
        return queryset.filter(branch_id=value)

    def filter_keyword(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(name__icontains=value) |
            Q(phone__icontains=value)
        )
