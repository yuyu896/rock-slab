from rest_framework import serializers
from .models import InventoryTask, InventoryItem, InventoryCheck


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = [
            'id', 'task', 'asset', 'expected_qty', 'actual_qty',
            'result', 'check_count', 'checked_by', 'checked_at',
            'remarks', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class InventoryCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryCheck
        fields = [
            'id', 'task', 'item', 'asset', 'qty',
            'checked_by', 'checked_at', 'device',
        ]
        read_only_fields = ['checked_at']


class InventoryTaskSerializer(serializers.ModelSerializer):
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
    asset_id = serializers.CharField()
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
