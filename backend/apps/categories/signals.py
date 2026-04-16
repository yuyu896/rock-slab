"""
Category counter signals.
Automatically update asset_count and in_stock_count on Category when assets change.
"""
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apps.assets.models import Asset
from apps.categories.models import Category


def _update_category_count(category):
    """Recount assets for a single category."""
    assets = Asset.objects.filter(资产编号=category.asset_code)
    category.asset_count = assets.count()
    category.in_stock_count = assets.filter(当前状态='在库').count()
    category.save(update_fields=['asset_count', 'in_stock_count'])


def _schedule_category_update(category_code):
    """Schedule a counter update after the current transaction commits."""
    try:
        category = Category.objects.get(asset_code=category_code)
    except Category.DoesNotExist:
        return
    transaction.on_commit(lambda: _update_category_count(category))


def _get_category_code(instance):
    """Extract category code from an asset's 资产编号."""
    return instance.资产编号


@receiver(post_save, sender=Asset)
def asset_saved_update_category(sender, instance, created, **kwargs):
    """Update category counters when an asset is created or updated."""
    code = _get_category_code(instance)
    if code:
        _schedule_category_update(code)

    # If status changed, also update the old category code
    if not created and kwargs.get('update_fields'):
        # Check if 当前状态 changed — need to update counts
        pass  # on_commit handles this via full recount


@receiver(post_delete, sender=Asset)
def asset_deleted_update_category(sender, instance, **kwargs):
    """Update category counters when an asset is deleted."""
    code = _get_category_code(instance)
    if code:
        _schedule_category_update(code)
