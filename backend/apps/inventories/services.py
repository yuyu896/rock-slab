"""盘点领域服务：差异项 → 台账调整单（P3 盘点差异自动生成调整单）。"""
from apps.assets.services import ledger as ledger_service
from .models import InventoryItem


def generate_variance_adjustments(task, approver):
    """审批通过钩子（_transition 锁内事务）中调用：逐差异项经唯一写入口开单修账。

    目标列=在库数量（盘点只盘在库列，expected 取自在库）；漏盘归零规则(zero)
    已把漏盘项写成 actual=0/missing，keep 规则的未盘项保持 unchecked 不开单；
    任一行致负数由 apply_adjustment 抛 LEDGER_INSUFFICIENT，外层事务整笔回滚。
    """
    adjustments = []
    items = (
        InventoryItem.objects
        .filter(task=task, result__in=['surplus', 'missing'])
        .exclude(actual_qty__isnull=True)
        .select_related('stock__branch', 'stock__item')
        .order_by('id')
    )
    for entry in items:
        delta = entry.actual_qty - entry.expected_qty
        if delta == 0:
            continue
        label = '盘盈' if delta > 0 else '盘亏'
        stock = entry.stock
        adjustments.append(ledger_service.apply_adjustment(
            branch=stock.branch,
            item=stock.item,
            column=ledger_service.COLUMN_STOCK,
            delta=delta,
            reason=(
                f'盘点差异「{task.name}」：在库 {entry.expected_qty} → '
                f'{entry.actual_qty}（{label}{abs(delta)}）'
            ),
            operator=approver,
            source_task=task,
        ))
    return adjustments
