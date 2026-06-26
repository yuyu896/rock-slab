from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import ProtectedError
from apps.permissions.permissions import OperationPermission
from .models import Region, Branch, Team
from .serializers import RegionSerializer, BranchSerializer, TeamSerializer
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
    queryset = Branch.objects.select_related('region', 'manager').all()
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
        team = serializer.save()
        self._assign_leader_team(team)

    def perform_update(self, serializer):
        team = serializer.save()
        self._assign_leader_team(team)

    def perform_destroy(self, instance):
        # 将所有成员的 team 置空
        instance.members.update(team=None)
        instance.delete()

    @staticmethod
    def _assign_leader_team(team):
        """若设置了 leader，自动将该 user 的 team 指向此 Team"""
        if team.leader_id and team.leader.team_id != team.id:
            team.leader.team = team
            team.leader.save(update_fields=['team', 'updated_at'])
