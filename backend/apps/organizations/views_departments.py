from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.permissions.permissions import OperationPermission
from core.pagination import StandardPagination
from .models import Department
from .serializers import DepartmentSerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    """部门字典（全集团扁平）：管理需 manage_organizations；options 端点供表单下拉（登录即可）。

    扁平字典无分公司维度，不做数据范围过滤（部门不参与数据范围推导，同品目字典待遇）。
    """

    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = StandardPagination
    required_operations = {
        'create': 'manage_organizations',
        'update': 'manage_organizations',
        'partial_update': 'manage_organizations',
        'destroy': 'manage_organizations',
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
