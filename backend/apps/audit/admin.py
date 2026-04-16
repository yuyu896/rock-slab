from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user_name', 'action', 'resource_type',
        'resource_name', 'is_success', 'ip_address', 'created_at',
    ]
    list_filter = ['action', 'is_success', 'resource_type']
    search_fields = ['user_name', 'resource_name', 'description']
    readonly_fields = [
        'user', 'user_name', 'user_phone', 'action', 'resource_type',
        'resource_id', 'resource_name', 'description', 'before_data',
        'after_data', 'ip_address', 'user_agent', 'request_path',
        'request_method', 'is_success', 'error_message', 'created_at',
    ]
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
