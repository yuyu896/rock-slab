from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, Max
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from core.permissions import IsRoleMin
from core.pagination import StandardPagination
from .models import AuditLog
from .serializers import AuditLogSerializer, AuditLogBriefSerializer
from .filters import AuditLogFilterSet

User = get_user_model()


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """审计日志视图集"""
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsRoleMin]
    pagination_class = StandardPagination
    filterset_class = AuditLogFilterSet
    min_role = 'admin'  # 仅管理员可查看
    ordering_fields = ['created_at', 'action']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return AuditLogBriefSerializer
        return AuditLogSerializer

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """操作统计 - 最近7天"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)

        # 按日期分组统计
        daily_stats = AuditLog.objects.filter(
            created_at__date__gte=week_ago,
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total=Count('id'),
            success=Count('id', filter=Q(is_success=True)),
            failed=Count('id', filter=Q(is_success=False)),
        ).order_by('-date')

        return Response(list(daily_stats))

    @action(detail=False, methods=['get'])
    def by_action(self, request):
        """按操作类型统计"""
        stats = AuditLog.objects.values('action').annotate(
            count=Count('id'),
        ).order_by('-count')

        return Response(list(stats))

    @action(detail=False, methods=['get'])
    def by_resource(self, request):
        """按资源类型统计"""
        stats = AuditLog.objects.values('resource_type').annotate(
            count=Count('id'),
        ).order_by('-count')[:20]

        return Response(list(stats))

    @action(detail=False, methods=['get'])
    def user_activity(self, request):
        """用户活跃度统计"""
        stats = AuditLog.objects.values(
            'user_id', 'user_name', 'user_phone'
        ).annotate(
            action_count=Count('id'),
            last_action=Max('created_at'),
        ).order_by('-action_count')[:20]

        return Response(list(stats))

    @action(detail=False, methods=['get'])
    def my_logs(self, request):
        """当前用户的操作日志"""
        queryset = AuditLog.objects.filter(
            user=request.user,
        ).order_by('-created_at')[:50]

        serializer = AuditLogBriefSerializer(queryset, many=True)
        return Response(serializer.data)
