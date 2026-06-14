import django_filters
from .models import Asset, FixedAsset


class AssetFilterSet(django_filters.FilterSet):
    branch = django_filters.CharFilter(field_name='分公司编号')
    category = django_filters.CharFilter(field_name='资产类目')
    status = django_filters.CharFilter(field_name='当前状态')
    keyword = django_filters.CharFilter(method='filter_keyword')

    ordering = django_filters.OrderingFilter(fields=(
        ('序号', '序号'),
        ('入库日期', '入库日期'),
        ('购入金额', '购入金额'),
        ('created_at', 'created_at'),
    ))

    class Meta:
        model = Asset
        fields = []

    def filter_keyword(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(资产名称__icontains=value) |
            Q(资产编号__icontains=value) |
            Q(分公司__icontains=value) |
            Q(使用人__icontains=value)
        )


class FixedAssetFilterSet(django_filters.FilterSet):
    branch = django_filters.CharFilter(field_name='分公司编号')
    asset_code = django_filters.CharFilter(field_name='资产编号')
    status = django_filters.CharFilter(field_name='当前状态')
    keyword = django_filters.CharFilter(method='filter_keyword')

    class Meta:
        model = FixedAsset
        fields = []

    def filter_keyword(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(内部编号__icontains=value) |
            Q(资产编号__icontains=value) |
            Q(资产名称__icontains=value) |
            Q(序列号__icontains=value) |
            Q(使用人__icontains=value)
        )
