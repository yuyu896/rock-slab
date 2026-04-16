"""Management command to recount all category asset counters."""
from django.core.management.base import BaseCommand
from apps.categories.models import Category
from apps.assets.models import Asset


class Command(BaseCommand):
    help = 'Recalculate asset_count and in_stock_count for all categories'

    def handle(self, *args, **options):
        categories = Category.objects.all()
        updated = 0
        for category in categories:
            assets = Asset.objects.filter(资产编号=category.asset_code)
            category.asset_count = assets.count()
            category.in_stock_count = assets.filter(当前状态='在库').count()
            category.save(update_fields=['asset_count', 'in_stock_count'])
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated} categories')
        )
