from rest_framework import serializers
from .models import Transfer


class TransferSerializer(serializers.ModelSerializer):
    """Serializer for Transfer model with Chinese field names used directly."""

    class Meta:
        model = Transfer
        fields = [
            'id',
            '调拨日期', '调出分公司', '调出部门', '调入分公司', '调入部门',
            '资产编号', '资产名称', '规格型号', '调拨数量', '调拨原因',
            '调出负责人', '调入负责人', '备注', '审批状态', '审批人',
            '审批时间', '创建人', 'action_type',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class TransferActionSerializer(serializers.Serializer):
    """Serializer for the 5 action routes (assign/return/transfer/repair/scrap)."""
    调拨日期 = serializers.DateField()
    资产编号 = serializers.CharField()
    资产名称 = serializers.CharField()
    调拨数量 = serializers.IntegerField(default=1)
    调拨原因 = serializers.CharField(required=False, default='')
    调出分公司 = serializers.CharField(required=False, default='')
    调出部门 = serializers.CharField(required=False, default='')
    调入分公司 = serializers.CharField(required=False, default='')
    调入部门 = serializers.CharField(required=False, default='')
    调出负责人 = serializers.CharField(required=False, default='')
    调入负责人 = serializers.CharField(required=False, default='')
    备注 = serializers.CharField(required=False, default='')
    创建人 = serializers.CharField(required=False, default='')


class ApproveSerializer(serializers.Serializer):
    """Serializer for the approve action."""
    approved = serializers.BooleanField()
    reason = serializers.CharField(required=False, default='')
