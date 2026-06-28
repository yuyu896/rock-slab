from django.db.models import Count, Sum, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.assets.models import Asset
from apps.transfers.models import Transfer
from apps.permissions.scope import resolve_user_scope


def _scope_queryset(user, queryset, branch_field=None, transfer_fields=None,
                    selected_branches=None):
    """按统一管理授权过滤查询集（与 DataScopeMixin.get_scoped_queryset 同源）。

    所有登录用户均可访问报表，但数据按其管理授权范围隔离：
    admin 或持有「全部数据」授权返回全集；其余按 ManagementScope 授权的分公司集合过滤；
    无授权的非 admin 返回空集（不再按角色硬编码放行，避免越权看到全公司数据）。
    已定义的全部角色（含 director）均按其授权范围处理，不被特殊降级。

    selected_branches：用户在筛选器选中的分公司 id 集合，用于在数据范围内进一步下钻。
    非 admin 时取与 scope.branches 的交集（防越权传入非授权分公司 id）；为空则不过滤。
    """
    scope = resolve_user_scope(user)
    if scope.all:
        qs = queryset
    else:
        q = Q()
        if scope.branches:
            if branch_field:
                q |= Q(**{f'{branch_field}__in': scope.branches})
            if transfer_fields:
                for f in transfer_fields:
                    q |= Q(**{f'{f}__in': scope.branches})
        if not q:
            return queryset.none()
        qs = queryset.filter(q).distinct()

    if selected_branches:
        if scope.all:
            allowed = set(selected_branches)
        else:
            # 与授权范围取交集（统一字符串比较，兼容 UUID），防越权传入非授权 id
            scope_str = {str(b) for b in scope.branches}
            allowed = {s for s in selected_branches if str(s) in scope_str}
        if not allowed:
            return qs.none()
        if branch_field:
            qs = qs.filter(**{f'{branch_field}__in': allowed})
        if transfer_fields:
            tq = Q()
            for f in transfer_fields:
                tq |= Q(**{f'{f}__in': allowed})
            qs = qs.filter(tq)
    return qs


def _parse_selected_branches(params):
    """解析 branches 查询参数（逗号分隔的分公司 id，UUID 字符串），返回 set 或 None。"""
    raw = (params.get('branches') or '').strip()
    if not raw:
        return None
    selected = {p.strip() for p in raw.split(',') if p.strip()}
    return selected or None


def _get_date_range_filter(params):
    """Parse optional dateRange param (format: 'YYYY-MM-DD,YYYY-MM-DD') into date filters."""
    date_range = params.get('dateRange')
    filters = {}
    if date_range:
        try:
            start_str, end_str = date_range.split(',')
            from datetime import datetime
            start = datetime.strptime(start_str.strip(), '%Y-%m-%d').date()
            end = datetime.strptime(end_str.strip(), '%Y-%m-%d').date()
            filters['入库日期__gte'] = start
            filters['入库日期__lte'] = end
        except (ValueError, AttributeError):
            pass
    return filters


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def branches(request):
    """返回当前用户数据范围内的分公司列表（供报表分公司筛选下拉）。

    admin 或「全部数据」授权返回全部分公司；其余仅返回其授权范围内的分公司，
    避免在下拉中泄露无权查看的分公司名称。
    """
    from apps.organizations.models import Branch
    scope = resolve_user_scope(request.user)
    qs = Branch.objects.all() if scope.all else Branch.objects.filter(id__in=scope.branches)
    data = [
        {'id': str(b.id), 'name': b.name, 'code': b.code}
        for b in qs.order_by('name')
    ]
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def overview(request):
    """报表概览: totalAssets, totalValue, activeRate, growthRate."""
    selected = _parse_selected_branches(request.query_params)
    filters = _get_date_range_filter(request.query_params)
    queryset = Asset.objects.all()
    queryset = _scope_queryset(
        request.user, queryset, branch_field='branch', selected_branches=selected,
    )

    if filters:
        queryset = queryset.filter(**filters)

    total_assets = queryset.count()
    total_value = queryset.aggregate(
        total=Sum('购入金额')
    )['total'] or 0

    # Active rate = assets in use or in stock vs total
    active_count = queryset.filter(
        当前状态__in=['在库', '使用中']
    ).count()
    active_rate = (active_count / total_assets * 100) if total_assets > 0 else 0

    # Growth rate: compare current month vs previous month
    now = timezone.now()
    current_month = queryset.filter(
        入库日期__year=now.year, 入库日期__month=now.month,
    ).count()
    prev_month_date = now.replace(day=1)
    if prev_month_date.month == 1:
        prev_year = prev_month_date.year - 1
        prev_month = 12
    else:
        prev_year = prev_month_date.year
        prev_month = prev_month_date.month - 1

    prev_month_count = queryset.filter(
        入库日期__year=prev_year, 入库日期__month=prev_month,
    ).count()

    if prev_month_count > 0:
        growth_rate = ((current_month - prev_month_count) / prev_month_count) * 100
    else:
        growth_rate = 100.0 if current_month > 0 else 0.0

    data = {
        'totalAssets': total_assets,
        'totalValue': total_value,
        'activeRate': round(active_rate, 2),
        'growthRate': round(growth_rate, 2),
    }
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def by_branch(request):
    """按分公司统计."""
    selected = _parse_selected_branches(request.query_params)
    filters = _get_date_range_filter(request.query_params)
    queryset = Asset.objects.all()
    queryset = _scope_queryset(
        request.user, queryset, branch_field='branch', selected_branches=selected,
    )
    if filters:
        queryset = queryset.filter(**filters)

    total = queryset.count()
    branch_stats = (
        queryset
        .values('分公司')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    data = []
    for stat in branch_stats:
        count = stat['count']
        percentage = (count / total * 100) if total > 0 else 0
        data.append({
            'name': stat['分公司'],
            'value': count,
            'percentage': round(percentage, 2),
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def by_status(request):
    """按状态统计."""
    selected = _parse_selected_branches(request.query_params)
    filters = _get_date_range_filter(request.query_params)
    queryset = Asset.objects.all()
    queryset = _scope_queryset(
        request.user, queryset, branch_field='branch', selected_branches=selected,
    )
    if filters:
        queryset = queryset.filter(**filters)

    total = queryset.count()
    status_stats = (
        queryset
        .values('当前状态')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    data = []
    for stat in status_stats:
        count = stat['count']
        percentage = (count / total * 100) if total > 0 else 0
        data.append({
            'status': stat['当前状态'],
            'count': count,
            'percentage': round(percentage, 2),
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def by_category(request):
    """按资产类目统计."""
    selected = _parse_selected_branches(request.query_params)
    filters = _get_date_range_filter(request.query_params)
    queryset = Asset.objects.all()
    queryset = _scope_queryset(
        request.user, queryset, branch_field='branch', selected_branches=selected,
    )
    if filters:
        queryset = queryset.filter(**filters)

    total = queryset.count()
    category_stats = (
        queryset
        .values('资产类目')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    data = []
    for stat in category_stats:
        count = stat['count']
        percentage = (count / total * 100) if total > 0 else 0
        data.append({
            'category': stat['资产类目'],
            'count': count,
            'percentage': round(percentage, 2),
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transfers(request):
    """调拨报表."""
    selected = _parse_selected_branches(request.query_params)
    queryset = Transfer.objects.all()
    queryset = _scope_queryset(
        request.user, queryset,
        transfer_fields=('from_branch', 'to_branch'), selected_branches=selected,
    )

    date_range = request.query_params.get('dateRange')
    if date_range:
        try:
            start_str, end_str = date_range.split(',')
            queryset = queryset.filter(
                调拨日期__gte=start_str.strip(),
                调拨日期__lte=end_str.strip(),
            )
        except (ValueError, AttributeError):
            pass

    # Filter by approval status
    status_filter = request.query_params.get('status')
    if status_filter:
        queryset = queryset.filter(审批状态=status_filter)

    # Filter by action type
    action_filter = request.query_params.get('type')
    if action_filter:
        queryset = queryset.filter(action_type=action_filter)

    queryset = queryset.order_by('-调拨日期')

    data = []
    for t in queryset:
        data.append({
            'id': str(t.id),
            'date': str(t.调拨日期),
            'assetCode': t.资产编号,
            'assetName': t.资产名称,
            'fromBranch': t.调出分公司,
            'toBranch': t.调入分公司,
            'quantity': t.调拨数量,
            'status': t.审批状态,
            'actionType': t.action_type,
        })
    return Response(data)
