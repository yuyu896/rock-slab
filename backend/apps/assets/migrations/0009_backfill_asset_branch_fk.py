"""回填存量 Asset.branch 外键（按分公司名匹配 Branch）。"""
from django.db import migrations


def backfill_branch_fk(apps, schema_editor):
    Asset = apps.get_model('assets', 'Asset')
    Branch = apps.get_model('organizations', 'Branch')
    name_to_branch = {b.name: b for b in Branch.objects.all()}
    updated = 0
    for asset in Asset.objects.filter(branch__isnull=True).exclude(分公司=''):
        branch = name_to_branch.get(asset.分公司)
        if branch:
            asset.branch = branch
            asset.save(update_fields=['branch'])
            updated += 1
    print(f'\n回填 Asset.branch: {updated} 条')


def reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0008_remove_fixedasset_unique_branch_serial'),
        ('organizations', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(backfill_branch_fk, reverse),
    ]
