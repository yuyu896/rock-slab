"""Populate Asset.branch FK from 分公司 CharField."""
from django.db import migrations


def populate_branch_fk(apps, schema_editor):
    Asset = apps.get_model('assets', 'Asset')
    Branch = apps.get_model('organizations', 'Branch')

    # Build a name -> id lookup
    branch_map = {b.name: b for b in Branch.objects.all()}

    unmatched = []
    matched = 0
    for asset in Asset.objects.all():
        branch_name = asset.分公司
        branch = branch_map.get(branch_name)
        if branch:
            asset.branch_id = branch.id
            asset.save(update_fields=['branch_id'])
            matched += 1
        else:
            unmatched.append((asset.id, branch_name))

    if unmatched:
        print(f'\n[WARNING] {len(unmatched)} assets with unmatched branch names:')
        for asset_id, name in unmatched[:20]:
            print(f'  Asset ID={asset_id}, 分公司="{name}"')
        if len(unmatched) > 20:
            print(f'  ... and {len(unmatched) - 20} more')
    print(f'[INFO] Populated branch FK for {matched}/{matched + len(unmatched)} assets')


def reverse_populate(apps, schema_editor):
    """No-op reverse — FK fields are nullable so clearing is safe."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0002_asset_branch_fk'),
        ('organizations', '0003_team'),
    ]

    operations = [
        migrations.RunPython(populate_branch_fk, reverse_populate),
    ]
