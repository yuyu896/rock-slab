from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.permissions.permissions import OperationPermission
from .models import ManagementScope, OperationGrant
from .operations import OPERATIONS
from .serializers import (
    ManagementScopeSerializer,
    OperationGrantSerializer,
)


class IsAdmin(OperationPermission):
    """仅 admin（走职位兜底）。"""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == 'admin')


class ManagementScopeViewSet(viewsets.ModelViewSet):
    """组织节点授权管理（仅 admin）。"""

    queryset = ManagementScope.objects.select_related('user', 'region', 'branch', 'team').all()
    serializer_class = ManagementScopeSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    # 授权记录数量小且按 user 过滤，关闭分页，直接返回数组（与前端 api 约定一致）
    pagination_class = None
    filterset_fields = ['user']
    search_fields = ['user__name', 'user__phone']


class OperationGrantViewSet(viewsets.ModelViewSet):
    """业务操作授权管理（仅 admin）。"""

    queryset = OperationGrant.objects.select_related('user').all()
    serializer_class = OperationGrantSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = None
    filterset_fields = ['user', 'code']
    search_fields = ['user__name', 'user__phone']


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def operation_catalog(request):
    """业务操作码目录（所有登录用户可读，供前端展示可勾选操作）。"""
    catalog = [{'code': k, 'label': v} for k, v in OPERATIONS.items()]
    return Response(catalog)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def position_templates(request):
    """岗位模板目录（岗位=权限预填模板，仅预填不参与运行时鉴权）。"""
    from .positions import POSITION_TEMPLATES
    data = [
        {
            'role': role,
            'label': tpl['label'],
            'scope_type': tpl['scope_type'],
            'operations': tpl['operations'] if tpl['operations'] is not None else list(OPERATIONS),
            'all_operations': tpl['operations'] is None,
        }
        for role, tpl in POSITION_TEMPLATES.items()
    ]
    return Response(data)


def _appointments_of(user):
    """某用户的树负责人任命清单（任命即授权的展示面）。"""
    from apps.organizations.models import Region, Team, Branch
    result = []
    for r in Region.objects.filter(manager=user):
        result.append({'type': 'region', 'id': str(r.id), 'name': r.name})
    for t in Team.objects.filter(leader=user):
        result.append({'type': 'team', 'id': str(t.id), 'name': t.name})
    for b in Branch.objects.filter(manager=user):
        result.append({'type': 'branch', 'id': str(b.id), 'name': b.name})
    return result


def _scope_summary_of(user):
    from .scope import resolve_user_scope
    scope = resolve_user_scope(user)
    if scope.all:
        return {'all': True, 'branch_count': None}
    return {'all': False, 'branch_count': len(scope.branches)}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def effective_permissions(request):
    """全员生效权限总览（仅 admin，矩阵页/生效权限卡数据源，实时派生）。"""
    from apps.users.models import User
    if request.user.role != 'admin':
        return Response({'detail': '无权操作'}, status=status.HTTP_403_FORBIDDEN)
    data = []
    for user in User.objects.filter(status='active').prefetch_related(
        'management_scopes', 'operation_grants',
    ).order_by('name'):
        if user.role == 'admin':
            data.append({
                'user': str(user.id), 'name': user.name, 'phone': user.phone,
                'role': user.role,
                'appointments': _appointments_of(user),
                'extra_scopes': [
                    {
                        'all': s.is_all_data,
                        'region': str(s.region_id) if s.region_id else None,
                        'team': str(s.team_id) if s.team_id else None,
                        'branch': str(s.branch_id) if s.branch_id else None,
                    }
                    for s in user.management_scopes.all()
                ],
                'operations': None,  # None = 全部（admin 内置）
                'scope_summary': {'all': True, 'branch_count': None},
            })
            continue
        data.append({
            'user': str(user.id), 'name': user.name, 'phone': user.phone,
            'role': user.role,
            'appointments': _appointments_of(user),
            'extra_scopes': [
                {
                    'all': s.is_all_data,
                    'region': str(s.region_id) if s.region_id else None,
                    'team': str(s.team_id) if s.team_id else None,
                    'branch': str(s.branch_id) if s.branch_id else None,
                }
                for s in user.management_scopes.all()
            ],
            'operations': list(user.operation_grants.values_list('code', flat=True)),
            'scope_summary': _scope_summary_of(user),
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_permissions(request):
    """当前用户的权限摘要（供前端消费；含任命节点与生效范围摘要）。"""
    from .serializers import UserPermissionSummarySerializer
    # 刷新实例以带出授权关系
    user = request.user.__class__.objects.prefetch_related(
        'management_scopes', 'operation_grants',
    ).get(pk=request.user.pk)
    data = UserPermissionSummarySerializer(user).data
    data['appointments'] = _appointments_of(user)
    data['scope_summary'] = _scope_summary_of(user)
    return Response(data)
