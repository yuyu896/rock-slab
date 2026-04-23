from rest_framework import serializers
from .models import Transfer
from apps.organizations.models import Branch


class TransferSerializer(serializers.ModelSerializer):
    """Serializer for Transfer model with Chinese field names used directly."""
    from_branch_name = serializers.CharField(source='from_branch.name', read_only=True, default=None)
    to_branch_name = serializers.CharField(source='to_branch.name', read_only=True, default=None)

    class Meta:
        model = Transfer
        fields = [
            'id',
            '调拨日期', '调出分公司', '调出部门', '调入分公司', '调入部门',
            '资产编号', '资产名称', '规格型号', '调拨数量', '调拨原因',
            '调出负责人', '调入负责人', '备注', '审批状态', '审批人',
            '审批时间', '创建人', 'action_type',
            '供应商', '单价', '总金额', '需求部门', '采购经办人', '用途',
            'from_branch', 'to_branch', 'from_branch_name', 'to_branch_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class TransferActionSerializer(serializers.Serializer):
    """Serializer for the 3 action routes (assign/return/transfer)."""
    调拨日期 = serializers.DateField()
    资产编号 = serializers.CharField()
    资产名称 = serializers.CharField()
    调拨数量 = serializers.IntegerField(default=1)
    调拨原因 = serializers.CharField(required=False, default='', allow_blank=True)
    调出分公司 = serializers.CharField(required=False, default='', allow_blank=True)
    调出部门 = serializers.CharField(required=False, default='', allow_blank=True)
    调入分公司 = serializers.CharField(required=False, default='', allow_blank=True)
    调入部门 = serializers.CharField(required=False, default='', allow_blank=True)
    调出负责人 = serializers.CharField(required=False, default='', allow_blank=True)
    调入负责人 = serializers.CharField(required=False, default='', allow_blank=True)
    备注 = serializers.CharField(required=False, default='', allow_blank=True)
    创建人 = serializers.CharField(required=False, default='', allow_blank=True)
    from_branch = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.none(), required=False, allow_null=True,
    )
    to_branch = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.none(), required=False, allow_null=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.organizations.models import Branch
        self.fields['from_branch'].queryset = Branch.objects.all()
        self.fields['to_branch'].queryset = Branch.objects.all()


class ApproveSerializer(serializers.Serializer):
    """Serializer for the approve action."""
    approved = serializers.BooleanField()
    reason = serializers.CharField(required=False, default='')
