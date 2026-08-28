from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import ProtectedError
from apps.permissions.permissions import OperationPermission
from apps.permissions.scope import resolve_user_scope
from .models import Region, Branch, Team, Company
from .serializers import RegionSerializer, BranchSerializer, TeamSerializer, CompanySerializer
from .filters import RegionFilterSet, BranchFilterSet


class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.select_related('manager').all()
    serializer_class = RegionSerializer
    filterset_class = RegionFilterSet
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = None
    # 写操作需 manage_organizations；读取无声明即放行
    required_operations = {
        'create': 'manage_organizations',
        'update': 'manage_organizations',
        'partial_update': 'manage_organizations',
        'destroy': 'manage_organizations',
    }

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            instance.delete()
        except ProtectedError:
            return Response(
                {'detail': '该区域下存在关联数据，无法删除。请先处理关联分公司。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.select_related('team', 'team__region', 'manager').all()
    serializer_class = BranchSerializer
    filterset_class = BranchFilterSet
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = None
    required_operations = {
        'create': 'manage_organizations',
        'update': 'manage_organizations',
        'partial_update': 'manage_organizations',
        'destroy': 'manage_organizations',
    }

    def get_queryset(self):
        """无参全量下发；scope=write 仅列授权范围内分公司（写单页下拉收口）。

        admin / 「全部数据」授权豁免；无授权用户返回空集——与提交端
        validate_branches_in_scope 口径一致（本来就无法对任何分公司写单）。
        """
        qs = super().get_queryset()
        if self.request.query_params.get('scope') == 'write':
            scope = resolve_user_scope(self.request.user)
            if not scope.all:
                qs = qs.filter(id__in=scope.branches)
        return qs

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            instance.delete()
        except ProtectedError:
            return Response(
                {'detail': '该分公司下存在关联资产，无法删除。请先将资产转移至其他分公司。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.select_related('region', 'leader').all()
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated, OperationPermission]
    pagination_class = None
    filterset_fields = ['region']
    required_operations = {
        'create': 'manage_organizations',
        'update': 'manage_organizations',
        'partial_update': 'manage_organizations',
        'destroy': 'manage_organizations',
    }

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            instance.delete()
        except ProtectedError:
            return Response(
                {'detail': '该行政组下存在分公司，无法删除。请先转移旗下分公司。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CompanyView(APIView):
    """集团（单例）：读所有登录用户，改名受 manage_organizations"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(CompanySerializer(Company.get_singleton()).data)

    def patch(self, request):
        if not request.user.can('manage_organizations'):
            return Response({'detail': '无权操作'}, status=status.HTTP_403_FORBIDDEN)
        company = Company.get_singleton()
        serializer = CompanySerializer(company, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
