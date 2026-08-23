import django_filters
from .models import Asset, AssetStock, FixedAsset


class AssetStockFilterSet(django_filters.FilterSet):
    branch = django_filters.CharFilter(field_name='branch__name')
    category = django_filters.CharFilter(field_name='item__asset_category')
    物品分类 = django_filters.CharFilter(field_name='item__item_category')
    management_type = django_filters.CharFilter(field_name='item__management_type')
    keyword = django_filters.CharFilter(method='filter_keyword')

    class Meta:
        model = AssetStock
        fields = []

    def filter_keyword(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(item__asset_name__icontains=value) |
            Q(item__asset_code__icontains=value) |
            Q(item__specification__icontains=value) |
            Q(branch__name__icontains=value)
        )


class AssetFilterSet(django_filters.FilterSet):
    branch = django_filters.CharFilter(field_name='分公司')
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
    branch = django_filters.CharFilter(field_name='分公司')
    asset_code = django_filters.CharFilter(field_name='资产编号')
    资产名称 = django_filters.CharFilter(field_name='资产名称')
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
