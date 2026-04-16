from rest_framework import serializers
from .models import Notification, ApprovalCC


class NotificationSerializer(serializers.ModelSerializer):
    """通知序列化器"""
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', read_only=True,
    )
    priority_display = serializers.CharField(
        source='get_priority_display', read_only=True,
    )

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'notification_type', 'notification_type_display',
            'title', 'content', 'priority', 'priority_display',
            'is_read', 'read_at', 'related_object_type', 'related_object_id',
            'extra_data', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'recipient', 'created_at', 'updated_at']


class ApprovalCCSerializer(serializers.ModelSerializer):
    """审批抄送序列化器"""
    cc_type_display = serializers.CharField(
        source='get_cc_type_display', read_only=True,
    )
    recipient_name = serializers.CharField(
        source='recipient.name', read_only=True,
    )

    class Meta:
        model = ApprovalCC
        fields = [
            'id', 'transfer', 'inventory_task', 'cc_type', 'cc_type_display',
            'cc_reason', 'recipient', 'recipient_name',
            'is_read', 'read_at', 'approval_snapshot',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
