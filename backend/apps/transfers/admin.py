from django.contrib import admin
from .models import Transfer


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = [
        '资产编号', '资产名称', '调拨日期', '调出分公司',
        '调入分公司', '调拨数量', '审批状态', 'action_type',
    ]
    list_filter = ['审批状态', 'action_type']
    search_fields = ['资产编号', '资产名称']
