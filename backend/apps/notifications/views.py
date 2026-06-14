from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q

from core.permissions import IsRoleMin
from core.pagination import StandardPagination
from .models import Notification, ApprovalCC
from .serializers import NotificationSerializer, ApprovalCCSerializer
from .filters import NotificationFilterSet, ApprovalCCFilterSet


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """通知视图集 - 只读 + 标记操作"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, IsRoleMin]
    pagination_class = StandardPagination
    filterset_class = NotificationFilterSet
    min_role = 'staff'

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user,
        ).select_related('recipient')

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """获取未读消息数量"""
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()
        return Response({'count': count})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """标记单条已读"""
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at', 'updated_at'])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """标记全部已读"""
        now = timezone.now()
        updated = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True, read_at=now)
        return Response({'detail': 'ok', 'updated': updated})

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """按类型分组统计"""
        from django.db.models import Count

        queryset = self.get_queryset()
        stats = queryset.values('notification_type').annotate(
            total=Count('id'),
            unread=Count('id', filter=Q(is_read=False)),
        )
        return Response(list(stats))


class ApprovalCCViewSet(viewsets.ReadOnlyModelViewSet):
    """抄送记录视图集"""
    serializer_class = ApprovalCCSerializer
    permission_classes = [IsAuthenticated, IsRoleMin]
    pagination_class = StandardPagination
    filterset_class = ApprovalCCFilterSet
    min_role = 'manager'  # 只有经理及以上可查看

    def get_queryset(self):
        return ApprovalCC.objects.filter(
            recipient=self.request.user,
        ).select_related('recipient', 'transfer', 'inventory_task')

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """标记已读"""
        cc = self.get_object()
        cc.is_read = True
        cc.read_at = timezone.now()
        cc.save(update_fields=['is_read', 'read_at', 'updated_at'])
        return Response(ApprovalCCSerializer(cc).data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """标记全部已读"""
        now = timezone.now()
        updated = ApprovalCC.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True, read_at=now)
        return Response({'detail': 'ok', 'updated': updated})
