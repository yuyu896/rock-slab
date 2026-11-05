from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, Max
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from core.permissions import IsAdmin
from core.pagination import StandardPagination
from .models import AuditLog
from .serializers import AuditLogSerializer, AuditLogBriefSerializer
from .filters import AuditLogFilterSet

User = get_user_model()


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """审计日志视图集"""
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination
    filterset_class = AuditLogFilterSet
    # Audit data is a system-administrator-only surface.
    ordering_fields = ['created_at', 'action']
    ordering = ['-created_at']

    @staticmethod
    def _resource_branch_ids(log):
        if not log.resource_id:
            return set()
        from apps.assets.models import AssetStock, FixedAsset, LedgerAdjustment
        from apps.inventories.models import InventoryTask
        from apps.reconciliation.models import ReconciliationComparison
        from apps.transfers.models import Transfer

        resource_type = log.resource_type
        resource_id = log.resource_id
        if resource_type == 'Transfer':
            row = Transfer.objects.filter(pk=resource_id).values_list('from_branch_id', 'to_branch_id').first()
            return {branch_id for branch_id in (row or ()) if branch_id}
        if resource_type == 'InventoryTask':
            return set(InventoryTask.objects.filter(pk=resource_id).values_list('branch_id', flat=True)) - {None}
        if resource_type == 'LedgerAdjustment':
            return set(LedgerAdjustment.objects.filter(pk=resource_id).values_list('branch_id', flat=True)) - {None}
        if resource_type == 'AssetStock':
            return set(AssetStock.objects.filter(pk=resource_id).values_list('branch_id', flat=True)) - {None}
        if resource_type in ('FixedAsset', 'Asset'):
            return set(FixedAsset.objects.filter(pk=resource_id).values_list('branch_id', flat=True)) - {None}
        if resource_type == 'ReconciliationTask':
            comparisons = ReconciliationComparison.objects.filter(version__task_id=resource_id)
            branch_ids = set(comparisons.values_list('system_branch_id', flat=True)) - {None}
            branch_ids.update(comparisons.values_list('order_row__branch_id', flat=True))
            return branch_ids - {None}
        if resource_type == 'ReconciliationIssue':
            comparisons = ReconciliationComparison.objects.filter(issue_id=resource_id)
            branch_ids = set(comparisons.values_list('system_branch_id', flat=True)) - {None}
            branch_ids.update(comparisons.values_list('order_row__branch_id', flat=True))
            return branch_ids - {None}
        if resource_type in ('User', 'user_authorization'):
            branch_ids = set(User.objects.filter(pk=resource_id).values_list('branch_id', flat=True)) - {None}
            if not branch_ids:
                from apps.organizations.models import Branch
                candidates = []
                for snapshot in (log.before_data, log.after_data):
                    if isinstance(snapshot, dict):
                        employee = snapshot.get('employee', snapshot)
                        if isinstance(employee, dict):
                            candidate = employee.get('branch_id') or employee.get('branch')
                            if isinstance(candidate, dict):
                                candidate = candidate.get('id')
                            if candidate:
                                candidates.append(candidate)
                branch_ids.update(Branch.objects.filter(pk__in=candidates).values_list('id', flat=True))
            return branch_ids
        return set()

    def get_queryset(self):
        queryset = super().get_queryset()
        from apps.permissions.scope import resolve_user_scope

        scope = resolve_user_scope(self.request.user)
        if self.request.user.role == 'admin' or scope.all:
            return queryset

        allowed = set(scope.branches)
        visible_ids = []
        # ``select_related('user')`` requires the foreign-key column to remain
        # selected. Keep the mapper's small field set and include ``user_id``.
        for log in queryset.only(
            'id', 'user_id', 'resource_id', 'resource_type',
            'before_data', 'after_data',
        ):
            if self._resource_branch_ids(log) & allowed:
                visible_ids.append(log.id)
        return queryset.filter(pk__in=visible_ids)

    def _hide_unscoped_snapshots(self, response):
        from apps.permissions.scope import resolve_user_scope

        if self.request.user.role == 'admin' or resolve_user_scope(self.request.user).all:
            return response
        if isinstance(response.data, dict):
            response.data['before_data'] = None
            response.data['after_data'] = None
        return response

    def retrieve(self, request, *args, **kwargs):
        return self._hide_unscoped_snapshots(super().retrieve(request, *args, **kwargs))

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
        daily_stats = self.get_queryset().filter(
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
        stats = self.get_queryset().values('action').annotate(
            count=Count('id'),
        ).order_by('-count')

        return Response(list(stats))

    @action(detail=False, methods=['get'])
    def by_resource(self, request):
        """按资源类型统计"""
        stats = self.get_queryset().values('resource_type').annotate(
            count=Count('id'),
        ).order_by('-count')[:20]

        return Response(list(stats))

    @action(detail=False, methods=['get'])
    def user_activity(self, request):
        """用户活跃度统计"""
        stats = self.get_queryset().values(
            'user_id', 'user_name', 'user_phone'
        ).annotate(
            action_count=Count('id'),
            last_action=Max('created_at'),
        ).order_by('-action_count')[:20]

        return Response(list(stats))

    @action(detail=False, methods=['get'])
    def my_logs(self, request):
        """当前用户的操作日志"""
        queryset = self.get_queryset().filter(user=request.user).order_by('-created_at')[:50]

        serializer = AuditLogBriefSerializer(queryset, many=True)
        return Response(serializer.data)
