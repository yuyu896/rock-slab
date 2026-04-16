from django.contrib import admin
from .models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = [
        '资产编号', '资产名称', '分公司', '当前状态',
        '数量', '使用人', '入库日期',
    ]
    list_filter = ['当前状态', '资产类目', '物品分类']
    search_fields = ['资产编号', '资产名称', '使用人']
