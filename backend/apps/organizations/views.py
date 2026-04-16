from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsRoleMin
from .models import Region, Branch, Team
from .serializers import RegionSerializer, BranchSerializer, TeamSerializer
from .filters import RegionFilterSet, BranchFilterSet


class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.select_related('manager').all()
    serializer_class = RegionSerializer
    filterset_class = RegionFilterSet
    permission_classes = [IsAuthenticated, IsRoleMin]
    pagination_class = None
    min_role = 'staff'  # 所有登录用户可查看

    def get_permissions(self):
        """创建/更新/删除需要管理员权限"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.min_role = 'admin'
        return super().get_permissions()


class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.select_related('region', 'manager').all()
    serializer_class = BranchSerializer
    filterset_class = BranchFilterSet
    permission_classes = [IsAuthenticated, IsRoleMin]
    pagination_class = None
    min_role = 'staff'  # 所有登录用户可查看

    def get_permissions(self):
        """创建/更新/删除需要管理员权限"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.min_role = 'admin'
        return super().get_permissions()


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.select_related('region', 'leader').all()
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated, IsRoleMin]
    pagination_class = None
    min_role = 'staff'
    filterset_fields = ['region']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.min_role = 'admin'
        return super().get_permissions()

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
