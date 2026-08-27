from rest_framework import serializers
from apps.organizations.models import Branch, Department
from .models import InventoryTask, InventoryItem, InventoryInstanceItem, InventoryCheck


class InventoryItemSerializer(serializers.ModelSerializer):
    asset_code = serializers.CharField(source='stock.item.asset_code', read_only=True)
    asset_name = serializers.CharField(source='stock.item.asset_name', read_only=True)
    branch_name = serializers.CharField(source='stock.branch.name', read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            'id', 'task', 'stock', 'asset_code', 'asset_name', 'branch_name',
            'expected_qty', 'actual_qty',
            'result', 'check_count', 'checked_by', 'checked_at',
            'remarks', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class InventoryCheckSerializer(serializers.ModelSerializer):
    checked_by_name = serializers.CharField(source='checked_by.name', read_only=True, default='')
    asset_code = serializers.CharField(source='stock.item.asset_code', read_only=True)
    asset_name = serializers.CharField(source='stock.item.asset_name', read_only=True)

    class Meta:
        model = InventoryCheck
        fields = [
            'id', 'task', 'item', 'stock', 'qty',
            'checked_by', 'checked_by_name', 'checked_at', 'device',
            'asset_code', 'asset_name',
        ]
        read_only_fields = ['checked_at']


class InventoryInstanceItemSerializer(serializers.ModelSerializer):
    """实例盘项 —— 逐台核对行（含实例档案展示字段与分组键）。"""

    instance_code = serializers.CharField(source='instance.内部编号', read_only=True)
    serial_number = serializers.CharField(source='instance.序列号', read_only=True)
    item_id = serializers.CharField(source='instance.item.id', read_only=True)
    unit = serializers.CharField(source='instance.item.unit', read_only=True)
    asset_code = serializers.CharField(source='instance.item.asset_code', read_only=True)
    asset_name = serializers.CharField(source='instance.item.asset_name', read_only=True)
    holder = serializers.CharField(source='instance.使用人', read_only=True)
    department = serializers.CharField(source='instance.department.name', read_only=True, default='')

    class Meta:
        model = InventoryInstanceItem
        fields = [
            'id', 'task', 'instance', 'instance_code', 'serial_number',
            'item_id', 'unit', 'asset_code', 'asset_name', 'holder', 'department',
            'result', 'check_count', 'checked_by', 'checked_at',
            'remarks', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class InventoryTaskSerializer(serializers.ModelSerializer):
    # 分公司必填（空值会触发全公司盘点项生成 + check 永远 404），创建后不可变更
    branch = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), required=True, allow_null=False,
    )
    inventory_kind = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True, default='')

    def get_inventory_kind(self, obj):
        return 'instance' if obj.is_instance_inventory else 'stock'

    class Meta:
        model = InventoryTask
        fields = [
            'id', 'name', 'branch', 'category', 'stock_bin', 'department', 'department_name',
            'status', 'missed_rule', 'repeat_rule', 'created_by', 'inventory_kind',
            'started_at', 'submitted_at', 'completed_at',
            'rejected_at', 'rejected_by', 'reject_reason',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            # 状态只经状态机动作流转，不接受 API 直改
            'status': {'read_only': True},
        }

    def validate(self, attrs):
        branch = attrs.get('branch') or getattr(self.instance, 'branch', None)
        department = attrs.get('department', getattr(self.instance, 'department', None))
        if department is not None and branch is not None and department.branch_id != branch.id:
            raise serializers.ValidationError(
                {'department': '盘点部门必须属于所选分公司'}
            )
        return attrs

    def update(self, instance, validated_data):
        validated_data.pop('branch', None)
        return super().update(instance, validated_data)


class InventoryTaskListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views."""

    inventory_kind = serializers.SerializerMethodField()

    class Meta:
        model = InventoryTask
        fields = [
            'id', 'name', 'branch', 'category', 'stock_bin', 'department', 'status',
            'missed_rule', 'repeat_rule', 'created_by', 'inventory_kind',
            'started_at', 'submitted_at', 'completed_at',
            'rejected_at', 'rejected_by', 'reject_reason',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_inventory_kind(self, obj):
        return 'instance' if obj.is_instance_inventory else 'stock'


class CheckItemSerializer(serializers.Serializer):
    """Serializer for the check action (single item check)."""
    stock_id = serializers.CharField()
    qty = serializers.IntegerField()
    remarks = serializers.CharField(required=False, default='')


class CheckInstanceSerializer(serializers.Serializer):
    """Serializer for the check-instance action (逐台核对)."""
    instance_id = serializers.CharField()
    found = serializers.BooleanField()
    remarks = serializers.CharField(required=False, default='')


class RejectSerializer(serializers.Serializer):
    """Serializer for the reject action."""
    reason = serializers.CharField()


class RecountSerializer(serializers.Serializer):
    """Serializer for the recount action (selective recount)."""
    reset_scope = serializers.ChoiceField(
        choices=['all', 'abnormal_only'],
        default='all',
        required=False,
    )


class InventoryProgressSerializer(serializers.Serializer):
    """Serializer for the progress read-only endpoint."""
    totalItems = serializers.IntegerField()
    checkedItems = serializers.IntegerField()
    matchedCount = serializers.IntegerField()
    surplusCount = serializers.IntegerField()
    missingCount = serializers.IntegerField()
    uncheckedCount = serializers.IntegerField()
    matchRate = serializers.FloatField(required=False)
    surplusRate = serializers.FloatField(required=False)
    missingRate = serializers.FloatField(required=False)


class InventoryReportSerializer(serializers.Serializer):
    """Serializer for the report read-only endpoint."""
    task = InventoryTaskSerializer()
    progress = InventoryProgressSerializer()
    items = InventoryItemSerializer(many=True)
