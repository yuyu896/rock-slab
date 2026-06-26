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
def my_permissions(request):
    """当前用户的权限摘要（供前端消费）。"""
    from .serializers import UserPermissionSummarySerializer
    # 刷新实例以带出授权关系
    user = request.user.__class__.objects.prefetch_related(
        'management_scopes', 'operation_grants',
    ).get(pk=request.user.pk)
    return Response(UserPermissionSummarySerializer(user).data)
