"""Populate expires_at for existing ExpiringTokens"""
from django.db import migrations
from django.utils import timezone


def populate_expires_at(apps, schema_editor):
    ExpiringToken = apps.get_model('authentication', 'ExpiringToken')
    for token in ExpiringToken.objects.filter(expires_at__isnull=True):
        token.expires_at = token.created + timezone.timedelta(days=30)
        token.save(update_fields=['expires_at'])


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_expiring_token'),
    ]

    operations = [
        migrations.RunPython(populate_expires_at, migrations.RunPython.noop),
    ]
