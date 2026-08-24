"""存量平铺单据 → 明细行 + 单据编号回填（P2 明细行化）。

纯 Python 逐行迭代（禁数据库特定聚合——SQLite/PG 行为一致）。
atomic=False：回填 DML 与后续 0013 的删列 DDL 分离，规避 PG 同事务 pending trigger events。
幂等：已回填（有明细行/有单据编号）的单据跳过。
"""
from django.db import migrations

PREFIXES = {'purchase': 'CG', 'assign': 'LY', 'return': 'GH', 'transfer': 'DB', 'recovery': 'HS'}


def backfill(apps, schema_editor):
    Transfer = apps.get_model('transfers', 'Transfer')
    TransferLine = apps.get_model('transfers', 'TransferLine')
    Category = apps.get_model('categories', 'Category')
    DocumentSequence = apps.get_model('transfers', 'DocumentSequence')

    # 字典编号 → 行（未登记编号的历史单据按户籍原则建存根）
    cat_by_code = {c.asset_code: c for c in Category.objects.all()}

    def resolve_item(code, name):
        code = (code or '').strip()
        if not code:
            code = f'UNK-{name or "未知"}'[:100]
        item = cat_by_code.get(code)
        if item is None:
            item = Category.objects.create(
                asset_code=code,
                asset_name=(name or '').strip() or code,
                asset_category='未分类',
                item_category='未分类',
                specification='',
                unit='件',
                management_type='quantity',
                is_rental=False,
                default_supplier='',
                remarks='存量单据迁移自动登记（编号入籍存根），请人工核对',
            )
            cat_by_code[code] = item
        return item

    for t in Transfer.objects.all().order_by('created_at'):
        if not TransferLine.objects.filter(transfer=t).exists():
            code = getattr(t, '资产编号', '') or ''
            item = resolve_item(code, getattr(t, '资产名称', '') or '')
            TransferLine.objects.create(
                transfer=t,
                item=item,
                行号=1,
                数量=max(int(getattr(t, '调拨数量', 0) or 0), 1),
                本批规格=getattr(t, '规格型号', '') or '',
                单价=getattr(t, '单价', None),
                金额=getattr(t, '总金额', None),
                存放位置=getattr(t, '存放位置', '') or '',
                固定资产内部编号=getattr(t, '固定资产内部编号', '') or '',
            )

        if not t.单据编号:
            doc_date = t.created_at.date()
            prefix = PREFIXES.get(t.action_type, 'DJ')
            seq, _ = DocumentSequence.objects.get_or_create(
                action_type=t.action_type, date=doc_date, defaults={'last_no': 0},
            )
            seq.last_no += 1
            seq.save(update_fields=['last_no', 'updated_at'])
            t.单据编号 = f'{prefix}{doc_date.strftime("%Y%m%d")}-{seq.last_no:03d}'
            t.save(update_fields=['单据编号', 'updated_at'])


def restore(apps, schema_editor):
    """回填不可逆（明细行/存根/编号保留），恢复走全量备份还原。"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('transfers', '0011_transferline_documentsequence_transfer_单据编号'),
    ]

    operations = [
        migrations.RunPython(backfill, restore, atomic=False),
    ]
