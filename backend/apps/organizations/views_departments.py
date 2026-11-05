from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.permissions.permissions import OperationPermission
from core.pagination import StandardPagination
from .models import Department
from .serializers import DepartmentSerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    """全集团扁平的部门字典；读取和维护分别受对应操作权限控制。

    options 端点与列表使用相同的查看权限。部门不参与数据范围推导。
    """

    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = StandardPagination
    required_operations = {
        'list': 'view_departments',
        'retrieve': 'view_departments',
        'options': 'view_departments',
        'assignee_options': ('change_instance_assignee', 'view_instances', 'view_departments'),
        'create': ('edit_departments', 'view_departments'),
        'update': ('edit_departments', 'view_departments'),
        'partial_update': ('edit_departments', 'view_departments'),
        'destroy': ('edit_departments', 'view_departments'),
    }

    def create(self, request, *args, **kwargs):
        from django.db import IntegrityError
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {'detail': '已存在同名部门'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=['get'], url_path='options')
    def options(self, request):
        """返回全集团部门选项（表单下拉）。"""
        return Response([
            {'id': str(d.id), 'name': d.name}
            for d in self.get_queryset().order_by('name')
        ])

    @action(detail=False, methods=['get'], url_path='assignee-options')
    def assignee_options(self, request):
        """仅供使用人变更表单选择部门；不开放部门字典页面权限。"""
        return Response([
            {'id': str(d.id), 'name': d.name}
            for d in self.get_queryset().order_by('name')
        ])
