import django_filters
from .models import Category


class CategoryFilterSet(django_filters.FilterSet):
    keyword = django_filters.CharFilter(method='filter_keyword')

    # Accept the Chinese field name as a filter param from the frontend
    资产类目 = django_filters.CharFilter(field_name='asset_category')
    物品分类 = django_filters.CharFilter(field_name='item_category')

    class Meta:
        model = Category
        fields = []

    def filter_keyword(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(asset_name__icontains=value) |
            Q(asset_code__icontains=value) |
            Q(asset_category__icontains=value) |
            Q(item_category__icontains=value)
        )
