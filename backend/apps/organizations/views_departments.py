from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.permissions.permissions import OperationPermission
from core.pagination import StandardPagination
from core.permissions import DataScopeMixin
from .models import Department
from .serializers import DepartmentSerializer


class DepartmentViewSet(DataScopeMixin, viewsets.ModelViewSet):
    """部门字典：管理需 manage_organizations；options 端点供表单下拉（登录即可）。"""

    queryset = Department.objects.select_related('branch').all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = StandardPagination
    scope_branch_field = 'branch'
    required_operations = {
        'create': 'manage_organizations',
        'update': 'manage_organizations',
        'partial_update': 'manage_organizations',
        'destroy': 'manage_organizations',
    }

    def get_queryset(self):
        qs = super().get_queryset()
        branch = self.request.query_params.get('branch')
        if branch:
            import uuid as _uuid
            try:
                _uuid.UUID(branch)
                qs = qs.filter(branch_id=branch)
            except (ValueError, AttributeError, TypeError):
                qs = qs.filter(branch__name=branch)
        return self.get_scoped_queryset(qs)

    def create(self, request, *args, **kwargs):
        from django.db import IntegrityError
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {'detail': '该分公司下已存在同名部门'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=['get'], url_path='options')
    def options(self, request):
        """按分公司返回部门选项（表单下拉）。"""
        branch_name = (request.query_params.get('branch') or '').strip()
        branch_id = (request.query_params.get('branch_id') or '').strip()
        qs = self.get_queryset()
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        elif branch_name:
            qs = qs.filter(branch__name=branch_name)
        return Response([
            {'id': str(d.id), 'name': d.name, 'branch': str(d.branch_id), 'branchName': d.branch.name}
            for d in qs.order_by('name')
        ])
