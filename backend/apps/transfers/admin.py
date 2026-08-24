from django.contrib import admin
from .models import Transfer, TransferLine


class TransferLineInline(admin.TabularInline):
    model = TransferLine
    extra = 0
    fields = ['行号', 'item', '数量', '本批规格', '单价', '金额', '使用人', 'department', '存放位置']
    autocomplete_fields = ['item']


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = [
        '单据编号', '调拨日期', '调出分公司',
        '调入分公司', '审批状态', 'action_type',
    ]
    list_filter = ['审批状态', 'action_type']
    search_fields = ['单据编号']
    inlines = [TransferLineInline]
