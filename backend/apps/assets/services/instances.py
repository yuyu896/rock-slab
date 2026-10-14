"""实例层唯一写入口 —— 实例状态/使用人/分公司的全部变动收敛于此（铁律 2 的实例版）。

由台账唯一写入口 ledger.apply_document 在同一事务内逐行调用；
禁止任何视图/导入/脚本直接改实例（架构测试 tests/test_ledger_migration_and_guard.py 执法）。

单据 × 实例对照（设计书 5.2/5.3，粒度 = 明细行）：
    采购入库     生成实例（在库，出生行=该行）
    领用(新品库) 所选在库实例 → 在用，写入使用人/部门
    领用(回收库) 所选回收库实例 → 在用，写入使用人/部门
    归还         清空使用人/部门 → 在库
    调拨         branch → 调入分公司（状态不变）
    回收重新入库 清空使用人/部门 → 在库
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


def expected_state(action_type, assign_source='stock', recovery_dest='restock'):
    """按单据类型/领用来源给出实例的合法前置状态集合；None 表示该类型不绑实例。"""
    if action_type == 'assign':
        return (
            (FixedAsset.STATUS_RECYCLE,)
            if assign_source == Transfer.ASSIGN_SOURCE_RECYCLE
            else (FixedAsset.STATUS_IN_STOCK,)
        )
    if action_type == 'return':
        return (FixedAsset.STATUS_IN_USE,)
    if action_type == 'transfer':
        return (FixedAsset.STATUS_IN_STOCK,)
    if action_type == 'recovery':
        # 处置向双源（在库/在用均可收）；重新入库仅收在用（recovery-stock-source-and-cleanup）
        if recovery_dest == 'dispose':
            return (FixedAsset.STATUS_IN_USE, FixedAsset.STATUS_IN_STOCK)
        return (FixedAsset.STATUS_IN_USE,)
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
                f'实例管理品目必须选择与数量等长的实例'
            )
        return
    if not is_instance_item:
        raise _err(
            f'非实例管理品目无需选择实例'
        )
    if transfer.action_type == 'purchase':
        raise _err(
            f'采购实例由入库自动生成，不可携带'
        )
    if transfer.action_type not in BINDING_ACTIONS:
        raise _err(f'该单据类型不支持实例引用')

    qty = int(line.数量 or 0)
    if len(instances) != qty:
        raise _err(
            f'实例数 {len(instances)} 与数量 {qty} 不一致'
        )

    want_state = expected_state(transfer.action_type, transfer.领用来源, transfer.回收去向)
    branch = (
        transfer.from_branch
        if transfer.action_type in ('assign', 'recovery', 'transfer')
        else (transfer.to_branch or transfer.from_branch)
    )
    for inst in instances:
        if inst.item_id != line.item_id:
            raise _err(
                f'实例 {inst.内部编号} 品目不符'
            )
        if inst.当前状态 not in want_state:
            hint = (
                '（在库实例无需回库；处置请改选「直接处置」）'
                if transfer.action_type == 'recovery' and transfer.回收去向 != 'dispose'
                and inst.当前状态 == FixedAsset.STATUS_IN_STOCK
                else ''
            )
            raise _err(
                f'实例 {inst.内部编号} '
                f'状态 {inst.当前状态} 不是 {"、".join(want_state)}（可能已被其他单据占用）{hint}'
            )
        if branch is not None and inst.branch_id != branch.pk:
            raise _err(
                f'实例 {inst.内部编号} 不在 {branch.name}'
            )


def _locked_sequence(item, branch):
    row = InstanceSequence.objects.select_for_update().filter(item=item, branch=branch).first()
    if row is None:
        try:
            with transaction.atomic():
                row = InstanceSequence.objects.create(item=item, branch=branch)
        except IntegrityError:
            row = InstanceSequence.objects.select_for_update().get(item=item, branch=branch)
    return row


def _existing_instance_numbers(item, branch, exclude_instance_ids=()):
    prefix = f'{item.asset_code}-{branch.code}-'
    existing = set()
    assets = FixedAsset.objects.filter(item=item, branch=branch)
    if exclude_instance_ids:
        assets = assets.exclude(pk__in=exclude_instance_ids)
    for (code,) in assets.values_list('内部编号'):
        if not code.startswith(prefix):
            continue
        tail = code[len(prefix):]
        if tail.isascii() and tail.isdigit():
            existing.add(int(tail))
    return existing


def _first_free_number(existing):
    candidate = 1
    while candidate in existing:
        candidate += 1
    return candidate


def next_available_instance_number(item, branch, exclude_instance_ids=()):
    """Return the lowest reusable serial without changing the sequence row."""
    return _first_free_number(
        _existing_instance_numbers(item, branch, exclude_instance_ids)
    )


def _allocate_no_gap_aware(item, branch, count):
    """按品目×分公司锁行分配最小空号；采购和调拨共用，退役档案仍占号。"""
    row = _locked_sequence(item, branch)
    existing = _existing_instance_numbers(item, branch)

    high_water = max(row.last_no, max(existing, default=0))
    numbers = []
    candidate = 1
    for _ in range(count):
        while candidate in existing:
            candidate += 1
        numbers.append(candidate)
        existing.add(candidate)
    if numbers:
        high_water = max(high_water, numbers[-1])
    if row.last_no != high_water:
        row.last_no = high_water
        row.save(update_fields=['last_no', 'updated_at'])
    return numbers


def _next_no_gap_aware(item, branch):
    """返回一个最小空号；多件采购通过批量分配避免重复扫描档案。"""
    return _allocate_no_gap_aware(item, branch, 1)[0]


def generate_instances(line, branch):
    """采购行生效：按数量生成实例（在库、出生行=该行、编号锁行发号）并建行关联。

    仅实例管理品目展开档案（设计书四层架构 ③）；数量管理品目只动台账，不产实例。
    编号 {品目编号}-{分公司代码}-{分公司内序号}。
    """
    if line.item.management_type != 'instance':
        return []
    created = []
    numbers = _allocate_no_gap_aware(line.item, branch, int(line.数量 or 0))
    for seq in numbers:
        instance = FixedAsset.objects.create(
            item=line.item,
            内部编号=f'{line.item.asset_code}-{branch.code}-{seq}',
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
        # 换号（transfer-instance-renumber）：过户+空号补位换号+前编号快照，同事务
        links = {lnk.instance_id: lnk for lnk in line.instance_links.all()}
        for inst in instances:
            old_code = inst.内部编号
            new_code = (f'{line.item.asset_code}-{transfer.to_branch.code}'
                        f'-{_next_no_gap_aware(line.item, transfer.to_branch)}')
            renumber_instance(inst, new_code)
            inst.内部编号 = new_code  # 内存对齐：末尾全字段 save 不得回滚换号
            inst.branch = transfer.to_branch
            inst.save(update_fields=['branch'])  # 立即落库：同事务后续取号可见，防同行多台重号
            lnk = links.get(inst.pk)
            if lnk is not None and not lnk.调拨前编号:
                lnk.调拨前编号 = old_code
                lnk.save(update_fields=['调拨前编号'])
    elif action == 'recovery':
        target = (
            FixedAsset.STATUS_RETIRED
            if transfer.回收去向 == Transfer.DISPOSE
            else FixedAsset.STATUS_IN_STOCK  # 重新入库：回收库概念退役
        )
        for inst in instances:
            inst.当前状态 = target
            _clear_assignee(inst)
    else:
        raise _err(f'单据类型 {action} 不存在实例迁移')
    for inst in instances:
        inst.save()


# ---------------------------------------------------------------------------
# 存量状态归一（P2 第二刀补丁）：旧导入时代的非法枚举 → 四态
# ---------------------------------------------------------------------------

# 同义映射依据：使用中=旧 Asset 枚举（FixedAsset 导入未校验混入）；空闲中=「空闲」变体
# （回收入库待再分配）；维修中按 P1 台账桶规则计入在用；已报废=出局终态
LEGACY_STATUS_MAP = {
    '使用中': FixedAsset.STATUS_IN_USE,
    '空闲中': FixedAsset.STATUS_RECYCLE,
    '空闲': FixedAsset.STATUS_RECYCLE,
    '维修中': FixedAsset.STATUS_IN_USE,
    '已报废': FixedAsset.STATUS_RETIRED,
}


def normalize_legacy_status():
    """非法状态枚举归一为四态；返回 [(原状态, 新状态, 条数)]，零改动返回 []。

    只动 当前状态 一列（分公司/台账/单据一概不碰）——用于数量管理品目挂着的
    历史死档（决断路线 A：品目维持数量管理，档案仅修展示层枚举）。
    """
    from django.db.models import Count

    stats = list(
        FixedAsset.objects.filter(当前状态__in=LEGACY_STATUS_MAP.keys())
        .order_by()
        .values('当前状态')
        .annotate(n=Count('id'))
    )
    if not stats:
        return []
    for row in stats:
        FixedAsset.objects.filter(当前状态=row['当前状态']).update(
            当前状态=LEGACY_STATUS_MAP[row['当前状态']],
        )
    return [
        (row['当前状态'], LEGACY_STATUS_MAP[row['当前状态']], row['n'])
        for row in stats
    ]

def recycle_bin_to_stock(inst):
    """回收库退役归一：单实例回收库→在库（清使用人/部门；一次性数据迁移用）。"""
    inst.当前状态 = FixedAsset.STATUS_IN_STOCK
    inst.使用人 = ''
    inst.department = None
    inst.save(update_fields=['当前状态', '使用人', 'department', 'updated_at'])
    return inst


def renumber_instance(inst, new_code):
    """存量重编号（一次性数据迁移用）：仅改 内部编号 一列。"""
    FixedAsset.objects.filter(pk=inst.pk).update(内部编号=new_code)
