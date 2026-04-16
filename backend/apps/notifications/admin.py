from django.contrib import admin
from .models import Notification, ApprovalCC


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'recipient', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'priority']
    search_fields = ['title', 'content', 'recipient__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ApprovalCC)
class ApprovalCCAdmin(admin.ModelAdmin):
    list_display = ['id', 'recipient', 'cc_type', 'transfer', 'inventory_task', 'is_read', 'created_at']
    list_filter = ['cc_type', 'is_read']
    search_fields = ['recipient__name']
    readonly_fields = ['created_at', 'updated_at']
