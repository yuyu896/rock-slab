from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """审计日志序列化器"""
    action_display = serializers.CharField(
        source='get_action_display', read_only=True,
    )

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_name', 'user_phone',
            'action', 'action_display', 'resource_type', 'resource_id', 'resource_name',
            'description', 'before_data', 'after_data',
            'ip_address', 'user_agent', 'request_path', 'request_method',
            'is_success', 'error_message',
            'created_at',
        ]
        read_only_fields = fields


class AuditLogBriefSerializer(serializers.ModelSerializer):
    """审计日志简要序列化器"""
    action_display = serializers.CharField(
        source='get_action_display', read_only=True,
    )

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user_name', 'action', 'action_display',
            'resource_type', 'resource_name',
            'is_success', 'created_at',
        ]
