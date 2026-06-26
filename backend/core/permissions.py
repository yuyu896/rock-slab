from django.db import models
from rest_framework.permissions import BasePermission

ROLE_LEVELS = {
    'admin': 1,
    'director': 2,
    'manager': 3,
    'supervisor': 4,
    'leader': 5,
    'staff': 6,
}


class IsRoleMin(BasePermission):
    """Restrict access by minimum role level. Set `min_role` on the view."""
    min_role = 'staff'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        min_level = ROLE_LEVELS.get(getattr(view, 'min_role', self.min_role), 99)
        user_level = ROLE_LEVELS.get(request.user.role, 99)
        return user_level <= min_level


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class CanApprove(BasePermission):
    """Supervisor and above (level <= 3) can approve."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and ROLE_LEVELS.get(request.user.role, 99) <= 3


class DataScopeMixin:
    """按管理授权过滤查询集（声明式字段映射）。

    各 ViewSet 在类上声明模型指向 Branch/Team 的字段：
        scope_branch_field = 'branch'                          # FK→Branch
        scope_transfer_fields = ('from_branch', 'to_branch')   # 双向分公司
        scope_team_field = '所属行政组'                          # FK→Team（如有）

    admin 返回全部；其余用户按其 ManagementScope 授权过滤；
    无授权的非 admin 返回空集（不再静默放行全部，避免越权）。
    """

    scope_branch_field = None
    scope_transfer_fields = None
    scope_team_field = None

    def get_scoped_queryset(self, queryset):
        from apps.permissions.scope import resolve_user_scope
        user = self.request.user
        scope = resolve_user_scope(user)
        if scope.all:
            return queryset

        q = models.Q()
        if scope.branches:
            if self.scope_branch_field:
                q |= models.Q(**{f'{self.scope_branch_field}__in': scope.branches})
            if self.scope_transfer_fields:
                for f in self.scope_transfer_fields:
                    q |= models.Q(**{f'{f}__in': scope.branches})
        if scope.teams and self.scope_team_field:
            q |= models.Q(**{f'{self.scope_team_field}__in': scope.teams})

        if not q:
            return queryset.none()
        return queryset.filter(q).distinct()
