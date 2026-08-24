"""台账唯一写入口 —— 所有数量变动收敛于此（铁律 2）。

禁止任何视图/导入/脚本直接改台账数量列；本模块是全项目唯一的台账写白名单
（架构测试 tests/test_ledger_architecture.py 执法）。

单据 × 数量对照（设计书 5.2，粒度 = 明细行）：
    采购入库    在库+N（无行则建行）
    领用        在库−N，在用+N（校验在库充足）
    归还        在用−N，在库+N
    调拨        调出在库−N（校验充足），调入在库+N（无行则建行）
    回收入回收库 在用−N，回收库+N
    回收直接处置 在用−N（三存储列均不增加，总量随之下跌）
    调整单      任一列 ±N（不可为负）
"""
from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from apps.assets.models import AssetStock, LedgerAdjustment

COLUMN_STOCK = '在库数量'
COLUMN_IN_USE = '在用数量'
COLUMN_RECYCLE = '回收库数量'
COLUMNS = (COLUMN_STOCK, COLUMN_IN_USE, COLUMN_RECYCLE)


def _locked_row(branch, item, create=True):
    """行锁取台账行；无行且 create 则返回未保存新行。"""
    row = (
        AssetStock.objects.select_for_update()
        .filter(branch=branch, item=item)
        .first()
    )
    if row is None and create:
        row = AssetStock(branch=branch, item=item)
    return row


def _apply_delta(row, column, delta):
    new_value = (getattr(row, column) or 0) + delta
    if new_value < 0:
        raise ValidationError({
            'detail': (
                f'「{row.branch.name} × {row.item.asset_code}」{column}不足：'
                f'当前 {getattr(row, column) or 0}，需变动 {delta:+d}'
            ),
            'code': 'LEDGER_INSUFFICIENT',
        })
    setattr(row, column, new_value)
    return new_value


def apply_adjustment(branch, item, column, delta, reason, operator=None, is_initial=False):
    """调整单入口：目标列 ±N，负数拒绝，留痕后返回调整单。"""
    if column not in COLUMNS:
        raise ValidationError({'detail': f'未知目标列 {column}'})
    with transaction.atomic():
        row = _locked_row(branch, item)
        _apply_delta(row, column, delta)
        row.save()
        return LedgerAdjustment.objects.create(
            branch=branch,
            item=item,
            目标列=column,
            变动量=delta,
            事由=reason,
            经办人=operator,
            is_initial=is_initial,
        )


def _line_plan(transfer, line):
    """一条明细行 → [(分公司, 品目, 目标列, 变动量)]，联动矩阵与设计书一字不变。"""
    item = line.item
    qty = int(line.数量 or 0)
    if qty <= 0:
        raise ValidationError({'detail': '数量必须为正'})
    action = transfer.action_type
    from_branch = transfer.from_branch
    to_branch = transfer.to_branch

    if action == 'purchase':
        branch = to_branch or from_branch
        return [(branch, item, COLUMN_STOCK, qty)]
    if action == 'assign':
        return [
            (from_branch, item, COLUMN_STOCK, -qty),
            (from_branch, item, COLUMN_IN_USE, qty),
        ]
    if action == 'return':
        branch = to_branch or from_branch
        return [
            (branch, item, COLUMN_IN_USE, -qty),
            (branch, item, COLUMN_STOCK, qty),
        ]
    if action == 'transfer':
        return [
            (from_branch, item, COLUMN_STOCK, -qty),
            (to_branch, item, COLUMN_STOCK, qty),
        ]
    if action == 'recovery':
        plan = [(from_branch, item, COLUMN_IN_USE, -qty)]
        if transfer.回收去向 == 'dispose':
            pass  # 直接处置：三存储列均不增加，总量随在用扣减下跌
        else:
            plan.append((from_branch, item, COLUMN_RECYCLE, qty))
        return plan
    raise ValidationError({'detail': f'未知单据类型 {action}'})


def _with_line_context(line, error):
    """错误信息补明细行定位（行号 × 品目编号）。"""
    detail = getattr(error, 'detail', None)
    msg = detail.get('detail') if isinstance(detail, dict) else str(detail or error)
    code = detail.get('code') if isinstance(detail, dict) else None
    return ValidationError({
        'detail': f'明细行 {line.行号}（{line.item.asset_code}）：{msg}',
        'code': code or 'LEDGER_ERROR',
    })


def apply_document(transfer):
    """流转单生效入口：明细行逐行执行联动矩阵。

    两阶段防死锁：先收集单据全部 (分公司, 品目) 依赖并按序一次性锁齐，
    再逐行变动——两张多行单据交叉审批不会形成环形等待。
    任一行充足性不足抛 ValidationError（LEDGER_INSUFFICIENT，带行号定位），
    调用方事务整体回滚，不存在部分生效。
    """
    lines = list(transfer.lines.select_related('item').order_by('行号'))
    if not lines:
        raise ValidationError({'detail': '单据缺少明细行'})

    action = transfer.action_type
    from_branch = transfer.from_branch
    to_branch = transfer.to_branch
    if action in ('purchase', 'return') and to_branch is None and from_branch is None:
        raise ValidationError({'detail': '单据缺少有效分公司维度'})
    if action == 'assign' and from_branch is None:
        raise ValidationError({'detail': '领用单缺少调出分公司'})
    if action == 'recovery' and from_branch is None:
        raise ValidationError({'detail': '回收单缺少调出分公司'})
    if action == 'transfer':
        if from_branch is None or to_branch is None:
            raise ValidationError({'detail': '调拨单缺少调出/调入分公司'})
        if from_branch.pk == to_branch.pk:
            raise ValidationError({'detail': '调出与调入分公司不能相同'})

    plans = [(line, _line_plan(transfer, line)) for line in lines]

    keys = sorted({
        (branch.pk, item.pk)
        for _, plan in plans
        for branch, item, _, _ in plan
    })
    lock_q = Q()
    for branch_pk, item_pk in keys:
        lock_q |= Q(branch_id=branch_pk, item_id=item_pk)

    with transaction.atomic():
        locked = {}
        if keys:
            rows = (
                AssetStock.objects.select_for_update()
                .filter(lock_q)
                .order_by('branch_id', 'item_id')
            )
            locked = {(r.branch_id, r.item_id): r for r in rows}

        touched = set()
        for line, plan in plans:
            try:
                for branch, item, column, delta in plan:
                    key = (branch.pk, item.pk)
                    row = locked.get(key)
                    if row is None:
                        row = AssetStock(branch=branch, item=item)
                        locked[key] = row
                    _apply_delta(row, column, delta)
                    touched.add(key)
            except ValidationError as error:
                raise _with_line_context(line, error)

        for key in sorted(touched):
            locked[key].save()
