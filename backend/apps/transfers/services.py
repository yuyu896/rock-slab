"""流转单领域服务：单据编号生成。"""
from django.db import IntegrityError, transaction

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
