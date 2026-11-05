from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.permissions.permissions import OperationPermission

from core.pagination import StandardPagination
from .models import Supplier
from .serializers import SupplierSerializer


class SupplierViewSet(viewsets.ModelViewSet):
    """供应商字典：查看和维护由独立账号级权限控制。

    扁平字典无分公司维度、不参与数据范围（同品目/部门字典待遇）。
    """

    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = StandardPagination
    required_operations = {
        'list': 'view_suppliers',
        'retrieve': 'view_suppliers',
        'create': ('edit_suppliers', 'view_suppliers'),
        'update': ('edit_suppliers', 'view_suppliers'),
        'partial_update': ('edit_suppliers', 'view_suppliers'),
        'destroy': ('edit_suppliers', 'view_suppliers'),
        'instance_options': ('edit_instances', 'view_suppliers'),
    }

    @action(detail=False, methods=['get'], url_path='instance-options')
    def instance_options(self, request):
        """Return only supplier IDs and names needed by instance editors."""
        options = Supplier.objects.order_by('name').values('id', 'name')
        return Response(list(options))
