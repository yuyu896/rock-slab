from rest_framework import serializers
from apps.organizations.models import Branch
from .models import InventoryTask, InventoryItem, InventoryCheck


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
    class Meta:
        model = InventoryCheck
        fields = [
            'id', 'task', 'item', 'stock', 'qty',
            'checked_by', 'checked_at', 'device',
        ]
        read_only_fields = ['checked_at']


class InventoryTaskSerializer(serializers.ModelSerializer):
    # 分公司必填（空值会触发全公司盘点项生成 + check 永远 404），创建后不可变更
    branch = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), required=True, allow_null=False,
    )

    class Meta:
        model = InventoryTask
        fields = [
            'id', 'name', 'branch', 'category', 'status',
            'missed_rule', 'repeat_rule', 'created_by',
            'started_at', 'submitted_at', 'completed_at',
            'rejected_at', 'rejected_by', 'reject_reason',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            # 状态只经状态机动作流转，不接受 API 直改
            'status': {'read_only': True},
        }

    def update(self, instance, validated_data):
        validated_data.pop('branch', None)
        return super().update(instance, validated_data)


class InventoryTaskListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views."""

    class Meta:
        model = InventoryTask
        fields = [
            'id', 'name', 'branch', 'category', 'status',
            'missed_rule', 'repeat_rule', 'created_by',
            'started_at', 'submitted_at', 'completed_at',
            'rejected_at', 'rejected_by', 'reject_reason',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class CheckItemSerializer(serializers.Serializer):
    """Serializer for the check action (single item check)."""
    stock_id = serializers.CharField()
    qty = serializers.IntegerField()
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
