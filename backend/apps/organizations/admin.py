from django.contrib import admin
from .models import Region, Branch


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'manager', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['name', 'code']


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'region', 'manager', 'status', 'created_at']
    list_filter = ['status', 'region']
    search_fields = ['name', 'code']
    raw_id_fields = ['region', 'manager']
