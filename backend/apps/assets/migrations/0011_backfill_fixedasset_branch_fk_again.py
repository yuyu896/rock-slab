"""再次回填 FixedAsset.branch 外键（按分公司名匹配，修复遗漏）。"""
from django.db import migrations


def backfill_branch_fk(apps, schema_editor):
    FixedAsset = apps.get_model('assets', 'FixedAsset')
    Branch = apps.get_model('organizations', 'Branch')
    name_to_branch = {b.name: b for b in Branch.objects.all()}
    updated = 0
    for fa in FixedAsset.objects.filter(branch__isnull=True).exclude(分公司=''):
        branch = name_to_branch.get(fa.分公司)
        if branch:
            fa.branch = branch
            fa.save(update_fields=['branch'])
            updated += 1
    print(f'\n回填 FixedAsset.branch (0011): {updated} 条')


def reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0010_backfill_fixedasset_branch_fk'),
        ('organizations', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(backfill_branch_fk, reverse),
    ]
