"""盘点领域服务：差异项 → 台账调整单（P3 盘点差异自动生成调整单）。"""
from apps.assets.services import ledger as ledger_service
from .models import InventoryItem, InventoryTask


def task_target_column(task):
    """台账盘差异目标列：固定在库数量（inventory-scope-rework——库别随范围分派下线，
    台账盘对象全是非实例品目，差异扣在库无歧义；存量 recycle 任务生产已清零，不兼容）。"""
    return ledger_service.COLUMN_STOCK


def generate_variance_adjustments(task, approver):
    """审批通过钩子（_transition 锁内事务）中调用：逐差异项经唯一写入口开单修账。

    目标列=任务库别对应列（应盘取自该列）；漏盘归零规则(zero)
    已把漏盘项写成 actual=0/missing，keep 规则的未盘项保持 unchecked 不开单；
    任一行致负数由 apply_adjustment 抛 LEDGER_INSUFFICIENT，外层事务整笔回滚。
    实例盘任务（department 非空）差异不自动改账，调用方不应传入。
    """
    adjustments = []
    column = task_target_column(task)
    bin_label = task.get_stock_bin_display()
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
        # 在用余额品目：差异或在用侧，提示人工核实（不自动改扣在用列）
        if (stock.在用数量 or 0) > 0:
            entry.remarks = (f'{entry.remarks}；' if entry.remarks else '') +                 f'该品目存在在用量 {stock.在用数量}，差异或在用侧，请人工核实'
            entry.save(update_fields=['remarks', 'updated_at'])
        adjustments.append(ledger_service.apply_adjustment(
            branch=stock.branch,
            item=stock.item,
            column=column,
            delta=delta,
            reason=(
                f'盘点差异「{task.name}」：{bin_label} {entry.expected_qty} → '
                f'{entry.actual_qty}（{label}{abs(delta)}）'
            ),
            operator=approver,
            source_task=task,
        ))
    return adjustments
