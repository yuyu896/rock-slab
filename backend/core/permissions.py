from django.db import models
from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class DataScopeMixin:
    """按管理授权过滤查询集（声明式字段映射）。

    各 ViewSet 在类上声明模型指向 Branch 的字段：
        scope_branch_field = 'branch'                          # FK→Branch
        scope_transfer_fields = ('from_branch', 'to_branch')   # 双向分公司

    授权范围由 resolve_user_scope 沿组织树展开为分公司集合
    （region → 行政组 → 分公司；team → 组内分公司）。

    admin 返回全部；其余用户按其 ManagementScope 授权过滤；
    无授权的非 admin 返回空集（不再静默放行全部，避免越权）。
    """

    scope_branch_field = None
    scope_transfer_fields = None

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

        if not q:
            return queryset.none()
        return queryset.filter(q).distinct()


def _branch_id(value):
    """Normalize a Branch instance / id / None to an id or None."""
    if value is None:
        return None
    return value.id if hasattr(value, 'id') else value


def validate_branches_in_scope(user, *branch_values):
    """写操作前校验：给定分公司（Branch 实例或 id）必须都在用户管理授权范围内。

    admin / 拥有「全部数据」授权的用户豁免；其余用户若任一目标分公司不在其
    resolve_user_scope 的 branches 内，抛 ValidationError。用于流转、盘点等
    写操作，防止越权改写其他区域的资产 / 库存。
    """
    from rest_framework.exceptions import ValidationError
    from apps.permissions.scope import resolve_user_scope

    scope = resolve_user_scope(user)
    if scope.all:
        return
    targets = {_branch_id(v) for v in branch_values if _branch_id(v) is not None}
    out_of_scope = targets - scope.branches
    if out_of_scope:
        raise ValidationError({'detail': '您只能操作授权范围内的分公司'})
