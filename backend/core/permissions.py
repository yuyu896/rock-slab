from django.db import models
from rest_framework.permissions import BasePermission

ROLE_LEVELS = {
    'admin': 1,
    'manager': 2,
    'supervisor': 3,
    'leader': 4,
    'staff': 5,
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
    """Filter querysets based on user role for data scoping."""

    def get_scoped_queryset(self, queryset):
        user = self.request.user
        if user.role in ('admin', 'manager'):
            return queryset
        model = queryset.model

        if user.role == 'supervisor' and getattr(user, 'region', None):
            # Prefer FK-based query if branch field exists
            if hasattr(model, 'branch') and not isinstance(
                getattr(model, 'branch', None), property
            ):
                try:
                    from django.db.models.fields.related import ForeignKey
                    field = model._meta.get_field('branch')
                    if isinstance(field, ForeignKey):
                        return queryset.filter(branch__region=user.region)
                except Exception:
                    pass
            # Fallback: Asset model CharField 分公司
            if hasattr(model, '分公司'):
                from apps.organizations.models import Branch
                branch_names = list(
                    Branch.objects.filter(region=user.region).values_list('name', flat=True)
                )
                return queryset.filter(分公司__in=branch_names)
            # Transfer model FK
            if hasattr(model, 'from_branch'):
                return queryset.filter(from_branch__region=user.region)
            return queryset

        if getattr(user, 'branch', None):
            if hasattr(model, 'branch') and not isinstance(
                getattr(model, 'branch', None), property
            ):
                try:
                    from django.db.models.fields.related import ForeignKey
                    field = model._meta.get_field('branch')
                    if isinstance(field, ForeignKey):
                        return queryset.filter(branch=user.branch)
                except Exception:
                    pass
            if hasattr(model, '分公司') and user.branch:
                return queryset.filter(分公司=user.branch.name)
            if hasattr(model, 'from_branch') and user.branch:
                return queryset.filter(
                    models.Q(from_branch=user.branch) | models.Q(to_branch=user.branch)
                )
            return queryset

        return queryset
