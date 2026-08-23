"""台账唯一写入口 —— 所有数量变动收敛于此（铁律 2）。

禁止任何视图/导入/脚本直接改台账数量列；本模块是全项目唯一的台账写白名单
（架构测试 tests/test_ledger_architecture.py 执法）。

单据 × 数量对照（设计书 5.2）：
    采购入库    在库+N（无行则建行）
    领用        在库−N，在用+N（校验在库充足）
    归还        在用−N，在库+N
    调拨        调出在库−N（校验充足），调入在库+N（无行则建行）
    回收入回收库 在用−N，回收库+N
    回收直接处置 在用−N（三存储列均不增加，总量随之下跌）
    调整单      任一列 ±N（不可为负）
"""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.assets.models import AssetStock, LedgerAdjustment

COLUMN_STOCK = '在库数量'
COLUMN_IN_USE = '在用数量'
COLUMN_RECYCLE = '回收库数量'
COLUMNS = (COLUMN_STOCK, COLUMN_IN_USE, COLUMN_RECYCLE)


def resolve_item(asset_code):
    """编号 → 品目字典行（未登记即拒绝，调用方已在创建时校验，此处兜底）。"""
    from apps.categories.models import Category
    item = Category.objects.filter(asset_code=asset_code).first()
    if item is None:
        raise ValidationError({'detail': f'资产编号 {asset_code} 未在品目字典登记'})
    return item


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


def apply_document(transfer):
    """流转单生效入口：按单据类型执行台账联动矩阵。

    须在调用方事务内或独立调用均可（内部自带事务，嵌套安全）。
    充足性不足抛 ValidationError（含 LEDGER_INSUFFICIENT 码），调用方回滚单据生效。
    """
    item = resolve_item(transfer.资产编号)
    qty = int(transfer.调拨数量 or 0)
    if qty <= 0:
        raise ValidationError({'detail': '单据数量必须为正'})

    action = transfer.action_type
    from_branch = transfer.from_branch
    to_branch = transfer.to_branch
    if action in ('purchase', 'return') and to_branch is None and from_branch is None:
        raise ValidationError({'detail': '单据缺少有效分公司维度'})

    with transaction.atomic():
        if action == 'purchase':
            branch = to_branch or from_branch
            row = _locked_row(branch, item)
            _apply_delta(row, COLUMN_STOCK, qty)
            row.save()
        elif action == 'assign':
            if from_branch is None:
                raise ValidationError({'detail': '领用单缺少调出分公司'})
            row = _locked_row(from_branch, item)
            _apply_delta(row, COLUMN_STOCK, -qty)
            _apply_delta(row, COLUMN_IN_USE, qty)
            row.save()
        elif action == 'return':
            branch = to_branch or from_branch
            row = _locked_row(branch, item)
            _apply_delta(row, COLUMN_IN_USE, -qty)
            _apply_delta(row, COLUMN_STOCK, qty)
            row.save()
        elif action == 'transfer':
            if from_branch is None or to_branch is None:
                raise ValidationError({'detail': '调拨单缺少调出/调入分公司'})
            if from_branch.pk == to_branch.pk:
                raise ValidationError({'detail': '调出与调入分公司不能相同'})
            src = _locked_row(from_branch, item, create=False)
            if src is None:
                raise ValidationError({
                    'detail': f'「{from_branch.name} × {item.asset_code}」无台账行，在库为 0，无法调拨 {qty}',
                    'code': 'LEDGER_INSUFFICIENT',
                })
            _apply_delta(src, COLUMN_STOCK, -qty)
            src.save()
            dst = _locked_row(to_branch, item)
            _apply_delta(dst, COLUMN_STOCK, qty)
            dst.save()
        elif action == 'recovery':
            if from_branch is None:
                raise ValidationError({'detail': '回收单缺少调出分公司'})
            row = _locked_row(from_branch, item)
            _apply_delta(row, COLUMN_IN_USE, -qty)
            if getattr(transfer, '回收去向', 'recycle_bin') == 'dispose':
                pass  # 直接处置：三存储列均不增加，总量随在用扣减下跌
            else:
                _apply_delta(row, COLUMN_RECYCLE, qty)
            row.save()
        else:
            raise ValidationError({'detail': f'未知单据类型 {action}'})
