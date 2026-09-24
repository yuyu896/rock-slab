"""流转单领域服务：单据编号生成 + 明细行实例引用创建预检。"""
from decimal import Decimal

from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from .models import DocumentSequence

DOC_NUMBER_PREFIXES = {
    'purchase': 'CG',
    'assign': 'LY',
    'return': 'GH',
    'transfer': 'DB',
    'recovery': 'HS',
    'adjust': 'TZ',
}


def _next_no(action_type, doc_date):
    """取 (类型, 日期) 的下一序号：已存在则锁行自增，首建免锁；并发首建由唯一约束兜底重试。"""
    with transaction.atomic():
        seq, created = DocumentSequence.objects.get_or_create(action_type=action_type, date=doc_date)
        if not created:
            seq = DocumentSequence.objects.select_for_update().get(pk=seq.pk)
        seq.last_no += 1
        seq.save(update_fields=['last_no', 'updated_at'])
        return seq.last_no


def generate_document_number(action_type, doc_date):
    """生成可读单据编号：{前缀}{YYYYMMDD}-{三位序号}，序号不足三位左补零、超三位自然展宽。"""
    prefix = DOC_NUMBER_PREFIXES.get(action_type, 'DJ')
    try:
        no = _next_no(action_type, doc_date)
    except IntegrityError:
        no = _next_no(action_type, doc_date)
    return f'{prefix}{doc_date.strftime("%Y%m%d")}-{no:03d}'


def validate_line_items_instances(action_type, from_branch, to_branch, assign_source, items,
                                  recovery_dest='restock'):
    """创建/编辑预检：品目管理方式 × 单据类型矩阵 + 类型专属行规则（生效时 ledger 另有行锁终检）。

    items 为序列化后的明细行字典（item 为品目实例、instances 为实例对象列表）。
    purchase 行金额留空在此补算（就地写回，表单/编辑/导入三路径同口径）。
    """
    from apps.assets.services import instances as instance_service

    seen = {}

    def err(row_no, code, msg):
        raise ValidationError({
            'detail': f'第 {row_no} 行（{code}）：{msg}',
            'code': 'INSTANCE_INVALID',
        })

    for row_no, entry in enumerate(items, start=1):
        item = entry['item']
        insts = entry.get('instances') or []
        if action_type == 'purchase':
            if insts:
                err(row_no, item.asset_code, '采购实例由入库自动生成，不可携带')
            # 金额留空自动 = 单价 × 数量（手填优先，无单价不补算）
            if entry.get('单价') is not None and entry.get('金额') is None:
                entry['金额'] = (Decimal(str(entry['单价'])) * entry['数量']).quantize(Decimal('0.01'))
            continue
        # 消耗品单据约束：无回收（领出已耗用出账）、无可归还（不进在用）、无回收库可领
        if item.management_type == 'consumable':
            if action_type == 'recovery':
                err(row_no, item.asset_code, '消耗品无回收：领出时已按耗用发放出账，如需修正走台账调整单')
            if action_type == 'return':
                err(row_no, item.asset_code, '消耗品无可归还：领用时不进在用')
            if action_type == 'assign' and assign_source == 'recycle_bin':
                err(row_no, item.asset_code, '消耗品无回收库存可领（领用来源仅支持新品库）')
        if action_type == 'assign':
            if not (entry.get('使用人') or '').strip():
                err(row_no, item.asset_code, '领用行必须填写使用人')
            if entry.get('department') is None:
                err(row_no, item.asset_code, '领用行必须选择领用部门')
        if action_type != 'purchase' and (entry.get('供应商') or '').strip():
            err(row_no, item.asset_code, '行级供应商仅采购行支持')
        if action_type == 'recovery' and recovery_dest != 'dispose'                 and item.management_type != 'instance':
            err(row_no, item.asset_code, '数量品物无重新入库概念（回库请走归还单；处置请改选「直接处置」）')
        if item.management_type != 'instance':
            if insts:
                err(row_no, item.asset_code, '非实例管理品目无需选择实例')
            continue
        if action_type not in instance_service.BINDING_ACTIONS:
            if insts:
                err(row_no, item.asset_code, '该单据类型不支持实例引用')
            continue
        if not insts:
            err(row_no, item.asset_code, '实例管理品目必须选择与数量等长的实例（请在页面单据中操作）')
        if len(insts) != entry['数量']:
            err(row_no, item.asset_code, f'实例数 {len(insts)} 与数量 {entry["数量"]} 不一致')

        want = instance_service.expected_state(action_type, assign_source, recovery_dest)
        branch = from_branch if action_type != 'return' else (to_branch or from_branch)
        for inst in insts:
            if inst.item_id != item.pk:
                err(row_no, item.asset_code, f'实例 {inst.内部编号} 品目不符')
            if inst.当前状态 not in want:
                hint = (
                    '（在库实例无需回库；处置请改选「直接处置」）'
                    if action_type == 'recovery' and recovery_dest != 'dispose'
                    and inst.当前状态 == '在库'
                    else ''
                )
                err(row_no, item.asset_code,
                    f'实例 {inst.内部编号} 状态 {inst.当前状态} 不是 {"、".join(want)}{hint}')
            if branch is not None and inst.branch_id != branch.pk:
                err(row_no, item.asset_code, f'实例 {inst.内部编号} 不在 {branch.name}')
            if inst.pk in seen:
                err(row_no, item.asset_code, f'实例 {inst.内部编号} 与第 {seen[inst.pk]} 行重复引用')
            seen[inst.pk] = row_no

    _validate_recovery_stock(action_type, from_branch, items, recovery_dest)


def _validate_recovery_stock(action_type, from_branch, items, recovery_dest):
    """回收数量品行充足软预检（处置向）：数量品物按（调出分公司×品目）合并计量
    扣在库（数量品不出库不领用、常态在库），超当前在库即拒。

    软预检不持锁（创建后账面仍可能变动，生效时行锁终检兜底）；重新入库向数量品
    已在上方矩阵拒绝，不进本函数。台账行缺失视为在库 0。
    """
    if action_type != 'recovery' or from_branch is None or recovery_dest != 'dispose':
        return
    from apps.assets.models import AssetStock

    totals = {}
    for entry in items:
        item = entry['item']
        if item.management_type != 'instance':
            totals.setdefault(item.pk, [item, 0])[1] += entry['数量']
    if not totals:
        return
    stocks = {
        s.item_id: s.在库数量
        for s in AssetStock.objects.filter(branch=from_branch, item_id__in=totals)
    }
    for _pk, (item, total) in sorted(totals.items()):
        stock = stocks.get(item.pk, 0)
        if total > stock:
            raise ValidationError({
                'detail': (
                    f'数量品物处置扣在库：当前在库 {stock}，需处置 {total}'
                    f'（{item.asset_code} {item.asset_name}）；'
                    f'若有在用余量请先走归还单收口'
                ),
                'code': 'LEDGER_INSUFFICIENT',
            })


def validate_disposal_fields(dest, method, amount):
    """处置必填校验（建单/编辑统一收口）：dispose→处置方式必填；出售→金额必填。"""
    if dest == 'dispose' and not method:
        raise ValidationError({'detail': '直接处置必须选择处置方式（出售/报废/捐赠）'})
    if method == '出售' and (amount is None or amount == ''):
        raise ValidationError({'detail': '处置方式为出售时必须填写处置金额'})
