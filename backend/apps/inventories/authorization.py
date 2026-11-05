"""Role- and scope-based approval eligibility for inventory tasks."""

from django.db.models import Q

from apps.permissions.scope import resolve_user_scope
from apps.users.models import User


def can_approve_inventory(user, task):
    if user.role == 'admin':
        return True
    if not user.can('review_inventory'):
        return False

    scope = resolve_user_scope(user)
    if task.branch_id is None:
        in_scope = scope.all
    else:
        in_scope = scope.all or task.branch_id in scope.branches
    if not in_scope:
        return False

    if user.role == 'manager':
        return task.created_by_id == user.id
    return user.role in ('leader', 'director')


def get_inventory_review_approvers(task):
    """Return eligible reviewers for notifications, based on role and live scope."""
    candidates = User.objects.filter(
        status='active',
    ).filter(
        Q(operation_grants__code='review_inventory') | Q(role='admin'),
    ).distinct()
    return [user for user in candidates if can_approve_inventory(user, task)]
