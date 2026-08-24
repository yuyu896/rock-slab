"""存量调整单回填单据编号——纯 Python 逐行发号（禁数据库聚合，SQLite/PG 同安全）。

按 created_at 升序取当日序号（TZ{YYYYMMDD}-{no}），幂等可重跑（仅处理编号为空的行）。
"""
from django.db import migrations


def backfill(apps, schema_editor):
    from apps.transfers.services import generate_document_number

    LedgerAdjustment = apps.get_model('assets', 'LedgerAdjustment')
    for adj in (
        LedgerAdjustment.objects.filter(单据编号__isnull=True)
        .order_by('created_at', 'id')
        .iterator()
    ):
        adj.单据编号 = generate_document_number('adjust', adj.created_at.date())
        adj.save(update_fields=['单据编号'])


def rewind(apps, schema_editor):
    LedgerAdjustment = apps.get_model('assets', 'LedgerAdjustment')
    LedgerAdjustment.objects.filter(单据编号__startswith='TZ').update(单据编号=None)


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0021_ledger_adjustment_doc_no_source'),
        ('transfers', '0016_drop_line_inner_code_text'),
    ]

    operations = [
        migrations.RunPython(backfill, rewind),
    ]
