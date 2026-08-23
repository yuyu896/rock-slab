from django.contrib import admin
from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        'asset_code', 'asset_category', 'item_category',
        'asset_name', 'management_type', 'unit', 'warning_line',
    ]
    list_filter = ['asset_category', 'item_category']
    search_fields = ['asset_code', 'asset_name']
