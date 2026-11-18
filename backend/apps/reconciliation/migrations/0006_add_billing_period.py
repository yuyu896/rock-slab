# Generated manually for billing period support

from django.db import migrations, models


def forwards(apps, schema_editor):
    """从现有订单行提取 billing_period"""
    Task = apps.get_model('reconciliation', 'ReconciliationTask')
    OrderRow = apps.get_model('reconciliation', 'ReconciliationOrderRow')

    for task in Task.objects.all():
        first_row = (
            OrderRow.objects
            .filter(version__task=task)
            .order_by('version__version_number', 'row_number')
            .first()
        )

        if first_row and first_row.accounting_date:
            task.billing_period = first_row.accounting_date.replace(day=1)
        else:
            task.billing_period = task.period

        task.save(update_fields=['billing_period'])


class Migration(migrations.Migration):

    dependencies = [
        ('reconciliation', '0005_remove_conclusion_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='reconciliationtask',
            name='billing_period',
            field=models.DateField(verbose_name='结算账期', null=True),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='reconciliationtask',
            name='billing_period',
            field=models.DateField(verbose_name='结算账期'),
        ),
        migrations.RemoveConstraint(
            model_name='reconciliationtask',
            name='uniq_recon_supplier_period',
        ),
        migrations.AddConstraint(
            model_name='reconciliationtask',
            constraint=models.UniqueConstraint(
                fields=['supplier', 'billing_period'],
                name='uniq_recon_supplier_billing_period'
            ),
        ),
        migrations.AlterModelOptions(
            name='reconciliationtask',
            options={'ordering': ['-billing_period', 'supplier__name']},
        ),
    ]
