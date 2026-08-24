"""实例层唯一写入口 —— 实例状态/使用人/分公司的全部变动收敛于此（铁律 2 的实例版）。

由台账唯一写入口 ledger.apply_document 在同一事务内逐行调用；
禁止任何视图/导入/脚本直接改实例（架构测试 tests/test_ledger_migration_and_guard.py 执法）。

单据 × 实例对照（设计书 5.2/5.3，粒度 = 明细行）：
    采购入库     生成实例（在库，出生行=该行）
    领用(新品库) 所选在库实例 → 在用，写入使用人/部门
    领用(回收库) 所选回收库实例 → 在用，写入使用人/部门
    归还         清空使用人/部门 → 在库
    调拨         branch → 调入分公司（状态不变）
    回收入回收库 清空使用人/部门 → 回收库
    回收直接处置 → 退役（终态，档案永久保留，绝不物理删除）
"""
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from apps.assets.models import FixedAsset, InstanceSequence
from apps.transfers.models import Transfer, TransferLineInstance

# 需要绑定既有实例的单据类型（采购为生成制，不在此列）
BINDING_ACTIONS = ('assign', 'return', 'transfer', 'recovery')


def _err(detail):
    return ValidationError({'detail': detail, 'code': 'INSTANCE_INVALID'})


def expected_state(action_type, assign_source='stock'):
    """按单据类型/领用来源给出实例的合法前置状态；None 表示该类型不绑实例。"""
    if action_type == 'assign':
        return (
            FixedAsset.STATUS_RECYCLE
            if assign_source == Transfer.ASSIGN_SOURCE_RECYCLE
            else FixedAsset.STATUS_IN_STOCK
        )
    if action_type in ('return', 'recovery'):
        return FixedAsset.STATUS_IN_USE
    if action_type == 'transfer':
        return FixedAsset.STATUS_IN_STOCK
    return None


def check_line_instances(transfer, line, instances):
    """终检一条明细行的实例引用（生效事务内、实例行锁后调用）。

    矩阵：实例管理品目 × 绑定类单据 必须数量等长、品目一致、状态/分公司匹配；
    采购行与数量管理品目行不得携带实例。
    """
    is_instance_item = line.item.management_type == 'instance'
    if not instances:
        if is_instance_item and transfer.action_type in BINDING_ACTIONS:
            raise _err(
                f'明细行 {line.行号}（{line.item.asset_code}）：实例管理品目必须选择与数量等长的实例'
            )
        return
    if not is_instance_item:
        raise _err(
            f'明细行 {line.行号}（{line.item.asset_code}）：数量管理品目无需选择实例'
        )
    if transfer.action_type == 'purchase':
        raise _err(
            f'明细行 {line.行号}（{line.item.asset_code}）：采购实例由入库自动生成，不可携带'
        )
    if transfer.action_type not in BINDING_ACTIONS:
        raise _err(f'明细行 {line.行号}：该单据类型不支持实例引用')

    qty = int(line.数量 or 0)
    if len(instances) != qty:
        raise _err(
            f'明细行 {line.行号}（{line.item.asset_code}）：实例数 {len(instances)} 与数量 {qty} 不一致'
        )

    want_state = expected_state(transfer.action_type, transfer.领用来源)
    branch = (
        transfer.from_branch
        if transfer.action_type in ('assign', 'recovery', 'transfer')
        else (transfer.to_branch or transfer.from_branch)
    )
    for inst in instances:
        if inst.item_id != line.item_id:
            raise _err(
                f'明细行 {line.行号}（{line.item.asset_code}）：实例 {inst.内部编号} 品目不符'
            )
        if inst.当前状态 != want_state:
            raise _err(
                f'明细行 {line.行号}（{line.item.asset_code}）：实例 {inst.内部编号} '
                f'状态 {inst.当前状态} 不是 {want_state}（可能已被其他单据占用）'
            )
        if branch is not None and inst.branch_id != branch.pk:
            raise _err(
                f'明细行 {line.行号}（{line.item.asset_code}）：实例 {inst.内部编号} 不在 {branch.name}'
            )


def _next_seq(item):
    row = InstanceSequence.objects.select_for_update().filter(item=item).first()
    if row is None:
        try:
            with transaction.atomic():
                row = InstanceSequence.objects.create(item=item)
        except IntegrityError:
            row = InstanceSequence.objects.select_for_update().get(item=item)
    row.last_no += 1
    row.save(update_fields=['last_no', 'updated_at'])
    return row.last_no


def generate_instances(line, branch):
    """采购行生效：按数量生成实例（在库、出生行=该行、编号锁行发号）并建行关联。"""
    created = []
    for _ in range(int(line.数量 or 0)):
        seq = _next_seq(line.item)
        instance = FixedAsset.objects.create(
            item=line.item,
            内部编号=f'{line.item.asset_code}-{seq}',
            当前状态=FixedAsset.STATUS_IN_STOCK,
            branch=branch,
            birth_line=line,
            入库日期=line.transfer.调拨日期,
        )
        TransferLineInstance.objects.create(line=line, instance=instance)
        created.append(instance)
    return created


def _clear_assignee(instance):
    instance.使用人 = ''
    instance.department = None


def apply_line_instances(transfer, line, instances):
    """绑定类单据行生效：迁移实例状态/使用人/分公司（终检通过后调用）。"""
    action = transfer.action_type
    if action == 'assign':
        for inst in instances:
            inst.当前状态 = FixedAsset.STATUS_IN_USE
            inst.使用人 = line.使用人
            inst.department = line.department
    elif action == 'return':
        for inst in instances:
            inst.当前状态 = FixedAsset.STATUS_IN_STOCK
            _clear_assignee(inst)
    elif action == 'transfer':
        for inst in instances:
            inst.branch = transfer.to_branch
    elif action == 'recovery':
        target = (
            FixedAsset.STATUS_RETIRED
            if transfer.回收去向 == Transfer.DISPOSE
            else FixedAsset.STATUS_RECYCLE
        )
        for inst in instances:
            inst.当前状态 = target
            _clear_assignee(inst)
    else:
        raise _err(f'单据类型 {action} 不存在实例迁移')
    for inst in instances:
        inst.save()
