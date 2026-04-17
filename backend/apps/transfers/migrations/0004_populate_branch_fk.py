"""Populate Transfer.from_branch/to_branch FK from CharField fields."""
from django.db import migrations


def populate_branch_fk(apps, schema_editor):
    Transfer = apps.get_model('transfers', 'Transfer')
    Branch = apps.get_model('organizations', 'Branch')

    branch_map = {b.name: b for b in Branch.objects.all()}

    unmatched_from = []
    unmatched_to = []
    matched_from = 0
    matched_to = 0
    to_update = []

    for transfer in Transfer.objects.all():
        changed = False

        from_name = transfer.调出分公司
        if from_name:
            branch = branch_map.get(from_name)
            if branch:
                transfer.from_branch_id = branch.id
                matched_from += 1
                changed = True
            elif from_name.strip():
                unmatched_from.append((transfer.id, from_name))

        to_name = transfer.调入分公司
        if to_name:
            branch = branch_map.get(to_name)
            if branch:
                transfer.to_branch_id = branch.id
                matched_to += 1
                changed = True
            elif to_name.strip():
                unmatched_to.append((transfer.id, to_name))

        if changed:
            to_update.append(transfer)

    Transfer.objects.bulk_update(to_update, ['from_branch_id', 'to_branch_id'])

    total = Transfer.objects.count()
    print(f'\n[INFO] Populated branch FK for transfers: from_branch={matched_from}, to_branch={matched_to}/{total}')

    for label, unmatched in [('from_branch', unmatched_from), ('to_branch', unmatched_to)]:
        if unmatched:
            print(f'[WARNING] {len(unmatched)} transfers with unmatched {label}:')
            for tid, name in unmatched[:10]:
                print(f'  Transfer ID={tid}, branch="{name}"')
            if len(unmatched) > 10:
                print(f'  ... and {len(unmatched) - 10} more')


def reverse_populate(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('transfers', '0003_transfer_branch_fk'),
        ('organizations', '0003_team'),
    ]

    operations = [
        migrations.RunPython(populate_branch_fk, reverse_populate),
    ]
