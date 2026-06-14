from django.db.models.signals import post_save, post_delete
from django.db import transaction
from .models import FixedAsset


def _sync_asset_counts(asset):
    """Recalculate quantity fields on the parent Asset."""
    from .models import Asset
    try:
        parent = Asset.objects.get(资产编号=asset.资产编号)
    except Asset.DoesNotExist:
        return
    instances = FixedAsset.objects.filter(资产编号=asset.资产编号)
    parent.数量 = instances.count()
    parent.save(update_fields=['数量', 'updated_at'])


def on_fixed_asset_save(sender, instance, **kwargs):
    if instance.asset_id:
        transaction.on_commit(lambda: _sync_asset_counts(instance))


def on_fixed_asset_delete(sender, instance, **kwargs):
    if instance.asset_id:
        transaction.on_commit(lambda: _sync_asset_counts(instance))


post_save.connect(on_fixed_asset_save, sender=FixedAsset)
post_delete.connect(on_fixed_asset_delete, sender=FixedAsset)
