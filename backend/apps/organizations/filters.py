import django_filters
from .models import Region, Branch


class RegionFilterSet(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    keyword = django_filters.CharFilter(method='filter_keyword')

    class Meta:
        model = Region
        fields = []

    def filter_keyword(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(name__icontains=value) | Q(code__icontains=value)
        )


class BranchFilterSet(django_filters.FilterSet):
    region = django_filters.CharFilter(field_name='region_id')
    status = django_filters.CharFilter(field_name='status')
    keyword = django_filters.CharFilter(method='filter_keyword')

    class Meta:
        model = Branch
        fields = []

    def filter_keyword(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(name__icontains=value) | Q(code__icontains=value)
        )
