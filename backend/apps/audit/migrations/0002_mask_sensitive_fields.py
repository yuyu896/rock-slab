"""清洗存量审计记录中的敏感字段（password 哈希等）。

与写入端共用 apps.audit.utils.mask_sensitive；纯 DML、幂等，
历史行中 sensitive 键值统一替换为 '***'，其余键不受影响。
"""
from django.db import migrations
from django.db.models import Q

from apps.audit.utils import mask_sensitive


def scrub_audit_rows(apps, schema_editor):
    AuditLog = apps.get_model('audit', 'AuditLog')
    rows = AuditLog.objects.filter(
        Q(before_data__isnull=False) | Q(after_data__isnull=False)
    ).iterator()
    for row in rows:
        changed = False
        for field in ('before_data', 'after_data'):
            data = getattr(row, field)
            if data:
                mask_sensitive(data)
                changed = True
        if changed:
            row.save(update_fields=['before_data', 'after_data'])


def unscrub_audit_rows(apps, schema_editor):
    # 脱敏不可逆（哈希本就不该留存），回滚为无操作
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(scrub_audit_rows, unscrub_audit_rows),
    ]
