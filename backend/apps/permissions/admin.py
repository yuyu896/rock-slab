from django.contrib import admin
from .models import ManagementScope, OperationGrant


class ReadOnlyAuthorizationAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ManagementScope)
class ManagementScopeAdmin(ReadOnlyAuthorizationAdmin):
    list_display = ('id', 'user', 'region', 'branch', 'team', 'created_at')
    list_filter = ('region', 'branch', 'team')
    search_fields = ('user__name', 'user__phone')
    raw_id_fields = ('user', 'region', 'branch', 'team')


@admin.register(OperationGrant)
class OperationGrantAdmin(ReadOnlyAuthorizationAdmin):
    list_display = ('id', 'user', 'code', 'created_at')
    list_filter = ('code',)
    search_fields = ('user__name', 'user__phone')
    raw_id_fields = ('user',)
