"""流转单领域服务：单据编号生成 + 明细行实例引用创建预检。"""
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from .models import DocumentSequence

DOC_NUMBER_PREFIXES = {
    'purchase': 'CG',
    'assign': 'LY',
    'return': 'GH',
    'transfer': 'DB',
    'recovery': 'HS',
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


def validate_line_items_instances(action_type, from_branch, to_branch, assign_source, items):
    """创建/编辑预检：品目管理方式 × 单据类型矩阵（生效时 ledger 另有行锁终检）。

    items 为序列化后的明细行字典（item 为品目实例、instances 为实例对象列表）。
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
            continue
        if item.management_type != 'instance':
            if insts:
                err(row_no, item.asset_code, '数量管理品目无需选择实例')
            continue
        if action_type not in instance_service.BINDING_ACTIONS:
            if insts:
                err(row_no, item.asset_code, '该单据类型不支持实例引用')
            continue
        if not insts:
            err(row_no, item.asset_code, '实例管理品目必须选择与数量等长的实例（请在页面单据中操作）')
        if len(insts) != entry['数量']:
            err(row_no, item.asset_code, f'实例数 {len(insts)} 与数量 {entry["数量"]} 不一致')
        if action_type == 'assign' and not (entry.get('使用人') or '').strip():
            err(row_no, item.asset_code, '领用实例管理品目必须填写使用人')

        want = instance_service.expected_state(action_type, assign_source)
        branch = from_branch if action_type != 'return' else (to_branch or from_branch)
        for inst in insts:
            if inst.item_id != item.pk:
                err(row_no, item.asset_code, f'实例 {inst.内部编号} 品目不符')
            if inst.当前状态 != want:
                err(row_no, item.asset_code, f'实例 {inst.内部编号} 状态 {inst.当前状态} 不是 {want}')
            if branch is not None and inst.branch_id != branch.pk:
                err(row_no, item.asset_code, f'实例 {inst.内部编号} 不在 {branch.name}')
            if inst.pk in seen:
                err(row_no, item.asset_code, f'实例 {inst.内部编号} 与第 {seen[inst.pk]} 行重复引用')
            seen[inst.pk] = row_no
