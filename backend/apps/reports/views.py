from django.db.models import Count, Sum, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.assets.models import AssetStock
from apps.transfers.models import Transfer, TransferLine
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
    """报表概览（P1 台账口径）：总量=台账三列之和，购入金额=已生效采购单合计。"""
    selected = _parse_selected_branches(request.query_params)
    ledger = AssetStock.objects.all()
    ledger = _scope_queryset(
        request.user, ledger, branch_field='branch', selected_branches=selected,
    )
    totals = ledger.aggregate(
        stock=Sum('在库数量'), in_use=Sum('在用数量'), recycle=Sum('回收库数量'),
    )
    stock_qty = totals['stock'] or 0
    in_use_qty = totals['in_use'] or 0
    recycle_qty = totals['recycle'] or 0
    total_qty = stock_qty + in_use_qty + recycle_qty

    # 购入金额与增长：来自采购单（金额属单据层，铁律 #8）
    purchases = Transfer.objects.filter(
        action_type=Transfer.ACTION_PURCHASE, 审批状态__in=['已入库', '已通过'],
    )
    purchases = _scope_queryset(
        request.user, purchases,
        transfer_fields=('from_branch', 'to_branch'), selected_branches=selected,
    )
    total_value = purchases.aggregate(total=Sum('lines__金额'))['total'] or 0

    now = timezone.now()
    current_month_qty = purchases.filter(
        调拨日期__year=now.year, 调拨日期__month=now.month,
    ).aggregate(q=Sum('lines__数量'))['q'] or 0
    if now.month == 1:
        prev_year, prev_month = now.year - 1, 12
    else:
        prev_year, prev_month = now.year, now.month - 1
    prev_month_purchases = purchases.filter(
        调拨日期__year=prev_year, 调拨日期__month=prev_month,
    )
    prev_month_qty = prev_month_purchases.aggregate(q=Sum('lines__数量'))['q'] or 0

    if prev_month_qty > 0:
        growth_rate = ((current_month_qty - prev_month_qty) / prev_month_qty) * 100
    else:
        growth_rate = 100.0 if current_month_qty > 0 else 0.0

    # 采购金额月环比（与数量环比同构，口径=本月 vs 上月已生效采购金额）
    current_month_value = purchases.filter(
        调拨日期__year=now.year, 调拨日期__month=now.month,
    ).aggregate(v=Sum('lines__金额'))['v'] or 0
    prev_month_value = prev_month_purchases.aggregate(
        v=Sum('lines__金额'),
    )['v'] or 0
    if prev_month_value > 0:
        value_growth_rate = ((current_month_value - prev_month_value) / prev_month_value) * 100
    else:
        value_growth_rate = 100.0 if current_month_value > 0 else 0.0

    from apps.assets.filters import insufficient_stock_q
    low_stock_count = ledger.filter(insufficient_stock_q()).count()

    active_qty = stock_qty + in_use_qty
    active_rate = (active_qty / total_qty * 100) if total_qty > 0 else 0

    return Response({
        'totalAssets': total_qty,
        'totalValue': total_value,
        'activeRate': round(active_rate, 2),
        'growthRate': round(growth_rate, 2),
        'valueGrowthRate': round(value_growth_rate, 2),
        'lowStockCount': low_stock_count,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def by_branch(request):
    """按分公司统计：数量=台账三列（时点快照），金额=已生效采购单明细行（入库分公司归属）。"""
    selected = _parse_selected_branches(request.query_params)
    ledger = AssetStock.objects.all()
    ledger = _scope_queryset(
        request.user, ledger, branch_field='branch', selected_branches=selected,
    )
    stats = (
        ledger.values('branch__name', 'branch__id')
        .annotate(
            stock=Sum('在库数量'), in_use=Sum('在用数量'),
            recycle=Sum('回收库数量'),
        )
        .order_by('-stock')
    )
    rows = []
    by_name = {}
    for s in stats:
        qty = (s['stock'] or 0) + (s['in_use'] or 0) + (s['recycle'] or 0)
        row = {
            'name': s['branch__name'],
            'branchId': str(s['branch__id']),
            'stock': s['stock'] or 0,
            'inUse': s['in_use'] or 0,
            'recycle': s['recycle'] or 0,
            'value': qty,
            'amount': 0,
            'percentage': 0,
        }
        rows.append(row)
        by_name[row['name']] = row

    # 采购金额并入同名分公司（入库分公司 = Coalesce(to_branch, from_branch)）
    purchases = Transfer.objects.filter(
        action_type=Transfer.ACTION_PURCHASE, 审批状态__in=['已入库', '已通过'],
    )
    purchases = _scope_queryset(
        request.user, purchases,
        transfer_fields=('from_branch', 'to_branch'), selected_branches=selected,
    )
    for p in purchases.values('to_branch__name', 'from_branch__name').annotate(
        amount=Sum('lines__金额'),
    ):
        name = p['to_branch__name'] or p['from_branch__name']
        row = by_name.get(name)
        if row is not None and p['amount']:
            row['amount'] += p['amount']

    total = sum(r['value'] for r in rows)
    total_amount = sum(r['amount'] for r in rows)
    for r in rows:
        r['percentage'] = round((r['value'] / total * 100), 2) if total > 0 else 0
        r['amountPercentage'] = (
            round((r['amount'] / total_amount * 100), 2) if total_amount > 0 else 0
        )
    rows.sort(key=lambda r: r['value'], reverse=True)
    return Response(rows)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def by_status(request):
    """按状态统计（台账三列口径：在库/在用/回收库）。"""
    selected = _parse_selected_branches(request.query_params)
    ledger = AssetStock.objects.all()
    ledger = _scope_queryset(
        request.user, ledger, branch_field='branch', selected_branches=selected,
    )
    totals = ledger.aggregate(
        stock=Sum('在库数量'), in_use=Sum('在用数量'), recycle=Sum('回收库数量'),
    )
    rows = [
        ('在库', totals['stock'] or 0),
        ('在用', totals['in_use'] or 0),
        ('回收库', totals['recycle'] or 0),
    ]
    total = sum(q for _, q in rows)
    return Response([
        {
            'status': label,
            'count': qty,
            'percentage': round((qty / total * 100), 2) if total > 0 else 0,
        }
        for label, qty in rows
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def by_category(request):
    """按资产类目统计（台账总量口径，联品目字典）。"""
    selected = _parse_selected_branches(request.query_params)
    ledger = AssetStock.objects.select_related('item').all()
    ledger = _scope_queryset(
        request.user, ledger, branch_field='branch', selected_branches=selected,
    )
    stats = (
        ledger.values('item__asset_category')
        .annotate(qty=Sum('在库数量') + Sum('在用数量') + Sum('回收库数量'))
        .order_by('-qty')
    )
    total = sum(s['qty'] for s in stats)
    return Response([
        {
            'category': s['item__asset_category'],
            'count': s['qty'],
            'percentage': round((s['qty'] / total * 100), 2) if total > 0 else 0,
        }
        for s in stats
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def consumables(request):
    """部门消耗统计：已生效领用单中消耗品行，部门×品目分组、按月展开（现算聚合，不落表）。

    数量口径 = 明细行数量求和（金额折算不做，待真实需求另立）；
    月份列取单头调拨日期（TruncMonth）；空部门归「未归属」；
    分支归属 = from_branch（发放方），数据范围遵循统一授权过滤。
    """
    from django.db.models.functions import TruncMonth

    selected = _parse_selected_branches(request.query_params)
    lines = TransferLine.objects.filter(
        transfer__action_type=Transfer.ACTION_ASSIGN,
        transfer__审批状态='已通过',
        item__management_type='consumable',
    )
    lines = _scope_queryset(
        request.user, lines,
        transfer_fields=('transfer__from_branch',), selected_branches=selected,
    )

    date_range = request.query_params.get('dateRange')
    if date_range:
        try:
            start_str, end_str = date_range.split(',')
            lines = lines.filter(
                transfer__调拨日期__gte=start_str.strip(),
                transfer__调拨日期__lte=end_str.strip(),
            )
        except (ValueError, AttributeError):
            pass

    stats = (
        lines
        .annotate(month=TruncMonth('transfer__调拨日期'))
        .values(
            'department', 'department__name',
            'item', 'item__asset_code', 'item__asset_name', 'item__unit',
            'month',
        )
        .annotate(qty=Sum('数量'))
    )

    months = set()
    rows_by_key = {}
    for s in stats:
        month = s['month'].strftime('%Y-%m') if s['month'] else '未知'
        months.add(month)
        # 分组键含品目 FK；部门按 id（跨分公司同名部门分行可辨），空部门并组
        key = (s['department'] or '', s['item'])
        row = rows_by_key.get(key)
        if row is None:
            row = {
                'department': s['department__name'] or '未归属',
                'itemId': str(s['item']),
                'code': s['item__asset_code'],
                'name': s['item__asset_name'],
                'unit': s['item__unit'] or '',
                'quantities': {},
                'total': 0,
            }
            rows_by_key[key] = row
        qty = s['qty'] or 0
        row['quantities'][month] = row['quantities'].get(month, 0) + qty
        row['total'] += qty

    month_list = sorted(months)
    rows = sorted(rows_by_key.values(), key=lambda r: (r['department'], -r['total']))
    grand_total = {
        m: sum(r['quantities'].get(m, 0) for r in rows) for m in month_list
    }
    grand_total['total'] = sum(grand_total.values())
    return Response({
        'months': month_list,
        'rows': rows,
        'grandTotal': grand_total,
    })


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

    queryset = queryset.order_by('-调拨日期').prefetch_related('lines__item')

    data = []
    for t in queryset:
        for line in t.lines.all():
            data.append({
                'id': str(t.id),
                'date': str(t.调拨日期),
                'docNumber': t.单据编号,
                'assetCode': line.item.asset_code,
                'assetName': line.item.asset_name,
                'fromBranch': t.调出分公司,
                'toBranch': t.调入分公司,
                'quantity': line.数量,
                'status': t.审批状态,
                'actionType': t.action_type,
                'operator': t.创建人,
            })
    return Response(data)
