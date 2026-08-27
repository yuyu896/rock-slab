import django_filters
from django.db.models import F, Q
from .models import AssetStock, FixedAsset


def insufficient_stock_q():
    """不足行判定：在库 < 生效警戒线（行级优先，空回落品目默认）——与
    AssetStock.生效警戒线 property 语义一字不差，供筛选与报表计数共用。"""
    return (
        Q(警戒线__isnull=False, 在库数量__lt=F('警戒线')) |
        Q(item__warning_line__isnull=False, 警戒线__isnull=True, 在库数量__lt=F('item__warning_line'))
    )


class AssetStockFilterSet(django_filters.FilterSet):
    branch = django_filters.CharFilter(field_name='branch__name')
    category = django_filters.CharFilter(field_name='item__asset_category')
    物品分类 = django_filters.CharFilter(field_name='item__item_category')
    management_type = django_filters.CharFilter(field_name='item__management_type')
    asset_code = django_filters.CharFilter(field_name='item__asset_code')
    keyword = django_filters.CharFilter(method='filter_keyword')
    sufficient = django_filters.CharFilter(method='filter_sufficient')

    class Meta:
        model = AssetStock
        fields = []

    def filter_sufficient(self, queryset, name, value):
        if value in ('0', 'false', 'False'):
            return queryset.filter(insufficient_stock_q())
        if value in ('1', 'true', 'True'):
            return queryset.exclude(insufficient_stock_q())
        return queryset

    def filter_keyword(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(item__asset_name__icontains=value) |
            Q(item__asset_code__icontains=value) |
            Q(item__specification__icontains=value) |
            Q(branch__name__icontains=value)
        )


class FixedAssetFilterSet(django_filters.FilterSet):
    branch = django_filters.CharFilter(field_name='branch__name')
    status = django_filters.CharFilter(field_name='当前状态')
    asset_code = django_filters.CharFilter(field_name='item__asset_code')
    item_keyword = django_filters.CharFilter(method='filter_item_keyword')
    pending_serial = django_filters.CharFilter(method='filter_pending_serial')
    keyword = django_filters.CharFilter(method='filter_keyword')

    class Meta:
        model = FixedAsset
        fields = []

    def filter_item_keyword(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(item__asset_code__icontains=value) |
            Q(item__asset_name__icontains=value)
        )

    def filter_pending_serial(self, queryset, name, value):
        if value in ('1', 'true', 'True'):
            return queryset.filter(序列号='')
        if value in ('0', 'false', 'False'):
            return queryset.exclude(序列号='')
        return queryset

    def filter_keyword(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(内部编号__icontains=value) |
            Q(item__asset_code__icontains=value) |
            Q(item__asset_name__icontains=value) |
            Q(序列号__icontains=value) |
            Q(使用人__icontains=value)
        )
