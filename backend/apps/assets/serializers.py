from rest_framework import serializers
from .models import Asset


class AssetSerializer(serializers.ModelSerializer):
    """Serializer for Asset model with Chinese field names used directly."""
    branch_name = serializers.CharField(source='branch.name', read_only=True, default=None)

    class Meta:
        model = Asset
        fields = [
            'id',
            '序号', '分公司', '分公司编号', '资产编号',
            '资产类目', '物品分类', '资产名称', '规格',
            '供应商', '图片', '入库日期', '是否租用',
            '数量', '单价', '购入金额', '出库日期',
            '所属部门', '使用人', '当前状态', '警戒线',
            '是否充足', '电脑序列号', '备注',
            'branch', 'branch_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
