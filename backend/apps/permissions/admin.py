from django.contrib import admin
from .models import ManagementScope, OperationGrant


@admin.register(ManagementScope)
class ManagementScopeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'region', 'branch', 'team', 'created_at')
    list_filter = ('region', 'branch', 'team')
    search_fields = ('user__name', 'user__phone')
    raw_id_fields = ('user', 'region', 'branch', 'team')


@admin.register(OperationGrant)
class OperationGrantAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'code', 'created_at')
    list_filter = ('code',)
    search_fields = ('user__name', 'user__phone')
    raw_id_fields = ('user',)
