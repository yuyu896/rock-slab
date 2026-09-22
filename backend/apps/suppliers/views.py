from rest_framework import permissions, viewsets

from apps.permissions.views import IsAdmin
from core.pagination import StandardPagination
from .models import Supplier
from .serializers import SupplierSerializer


class SupplierViewSet(viewsets.ModelViewSet):
    """供应商字典：读（列表/选项）登录即可，写（增删改）仅系统管理员。

    扁平字典无分公司维度、不参与数据范围（同品目/部门字典待遇）。
    """

    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdmin()]
        return super().get_permissions()
