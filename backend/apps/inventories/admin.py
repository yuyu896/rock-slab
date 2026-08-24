from django.contrib import admin
from .models import InventoryTask, InventoryItem, InventoryCheck


@admin.register(InventoryTask)
class InventoryTaskAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'branch', 'category', 'status',
        'created_by', 'started_at', 'completed_at',
    ]
    list_filter = ['status']
    search_fields = ['name']
    raw_id_fields = ['branch', 'category', 'created_by', 'rejected_by']


class InventoryItemInline(admin.TabularInline):
    model = InventoryItem
    extra = 0
    readonly_fields = ['check_count']


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['task', 'stock', 'expected_qty', 'actual_qty', 'result', 'check_count']
    list_filter = ['result']
    raw_id_fields = ['task', 'stock', 'checked_by']


@admin.register(InventoryCheck)
class InventoryCheckAdmin(admin.ModelAdmin):
    list_display = ['task', 'item', 'stock', 'qty', 'checked_by', 'checked_at']
    raw_id_fields = ['task', 'item', 'stock', 'checked_by']
