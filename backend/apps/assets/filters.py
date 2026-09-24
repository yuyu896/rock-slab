import django_filters
from django.db.models import F, Q
from django_filters import BaseInFilter, CharFilter
from .models import AssetStock, FixedAsset


class BranchNameInFilter(BaseInFilter, CharFilter):
    """分公司多选（逗号分隔名称 → __in 并集）。"""


def insufficient_stock_q():
    """不足行判定：在库 < 生效警戒线（行级优先，空回落品目默认）——与
    AssetStock.生效警戒线 property 语义一字不差，供筛选与报表计数共用。"""
    return (
        Q(警戒线__isnull=False, 在库数量__lt=F('警戒线')) |
        Q(item__warning_line__isnull=False, 警戒线__isnull=True, 在库数量__lt=F('item__warning_line'))
    )


class AssetStockFilterSet(django_filters.FilterSet):
    branch = BranchNameInFilter(field_name='branch__name', lookup_expr='in')
    category = django_filters.CharFilter(field_name='item__asset_category')
    物品分类 = django_filters.CharFilter(field_name='item__item_category')
    management_type = django_filters.CharFilter(field_name='item__management_type')
    asset_code = django_filters.CharFilter(field_name='item__asset_code')
    keyword = django_filters.CharFilter(method='filter_keyword')
    sufficient = django_filters.CharFilter(method='filter_sufficient')
    # 指定列>0（写单页品目点选按扣数列收口）；支持逗号分隔多列 OR（回收处置=在库或在用）
    positive_column = django_filters.CharFilter(method='filter_positive_column')

    class Meta:
        model = AssetStock
        fields = []

    def filter_sufficient(self, queryset, name, value):
        if value in ('0', 'false', 'False'):
            return queryset.filter(insufficient_stock_q())
        if value in ('1', 'true', 'True'):
            return queryset.exclude(insufficient_stock_q())
        return queryset

    POSITIVE_COLUMNS = ('在库数量', '在用数量', '回收库数量')

    def filter_positive_column(self, queryset, name, value):
        from django.db.models import Q
        from rest_framework.exceptions import ValidationError
        cols = [c for c in (v.strip() for v in value.split(',')) if c]
        if any(c not in self.POSITIVE_COLUMNS for c in cols):
            raise ValidationError({'detail': f'非法列名：{value}（合法：在库数量/在用数量/回收库数量，逗号分隔）'})
        q = Q()
        for col in cols:
            q |= Q(**{f'{col}__gt': 0})
        return queryset.filter(q)

    def filter_keyword(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(item__asset_name__icontains=value) |
            Q(item__asset_code__icontains=value) |
            Q(item__specification__icontains=value) |
            Q(branch__name__icontains=value)
        )


class FixedAssetFilterSet(django_filters.FilterSet):
    branch = BranchNameInFilter(field_name='branch__name', lookup_expr='in')
    # 状态支持逗号分隔多值（回收处置=在库,在用）
    status = django_filters.CharFilter(method='filter_status_in')
    asset_code = django_filters.CharFilter(field_name='item__asset_code')
    item_keyword = django_filters.CharFilter(method='filter_item_keyword')
    pending_serial = django_filters.CharFilter(method='filter_pending_serial')
    keyword = django_filters.CharFilter(method='filter_keyword')
    # 点选器直达搜索（instance-picker-completeness）：内部编号/序列号 icontains
    inner_keyword = django_filters.CharFilter(method='filter_inner_keyword')

    def filter_inner_keyword(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(内部编号__icontains=value) | Q(序列号__icontains=value)
        )

    def filter_status_in(self, queryset, name, value):
        states = [v.strip() for v in value.split(',') if v.strip()]
        return queryset.filter(当前状态__in=states) if states else queryset

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
