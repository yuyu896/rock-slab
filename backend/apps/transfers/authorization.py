"""Per-document transfer permissions and approver routing."""

from django.db.models import Q

from .models import Transfer


TRANSFER_PERMISSION_CODES = {
    Transfer.ACTION_PURCHASE: {
        'create': 'edit_purchase',
        'view': 'view_purchase',
        'edit': 'edit_purchase',
        'delete': 'delete_purchase_draft',
        'submit': 'edit_purchase',
        'approve': 'approve_purchase',
        'withdraw': 'edit_purchase',
        'import': 'edit_purchase',
    },
    Transfer.ACTION_ASSIGN: {
        'create': 'edit_assignment',
        'view': 'view_assignment',
        'edit': 'edit_assignment',
        'delete': 'delete_assignment_draft',
        'submit': 'edit_assignment',
        'approve': 'approve_assignment',
        'withdraw': 'edit_assignment',
        'import': 'edit_assignment',
    },
    Transfer.ACTION_RETURN: {
        # Return is retired. Keep the historical action type recognizable to
        # reporting/audit code, but expose no user-facing permission route.
        'create': None,
        'view': None,
        'edit': None,
        'delete': None,
        'submit': None,
        'approve': None,
        'withdraw': None,
    },
    Transfer.ACTION_TRANSFER: {
        'create': 'edit_transfer',
        'view': 'view_transfer',
        'edit': 'edit_transfer',
        'delete': 'delete_transfer_draft',
        'submit': 'edit_transfer',
        'approve': 'approve_internal_transfer',
        'withdraw': 'edit_transfer',
        'import': 'edit_transfer',
    },
    Transfer.ACTION_RECOVERY: {
        'create': 'edit_recovery',
        'view': 'view_recovery',
        'edit': 'edit_recovery',
        'delete': 'delete_recovery_draft',
        'submit': 'edit_recovery',
        'approve': 'approve_recovery',
        'withdraw': 'edit_recovery',
    },
}


def transfer_permission_code(action_type, action):
    return TRANSFER_PERMISSION_CODES.get(action_type, {}).get(action)


def transfer_branch_id(action_type, from_branch_id, to_branch_id):
    if action_type in (Transfer.ACTION_PURCHASE, Transfer.ACTION_RETURN):
        return to_branch_id
    return from_branch_id


def _covers_branch(user, branch):
    from apps.permissions.scope import resolve_user_scope

    scope = resolve_user_scope(user)
    branch_id = branch.id if hasattr(branch, 'id') else branch
    return scope.all or (branch_id is not None and branch_id in scope.branches)


def _local_user_ids(users, branch):
    if branch is None:
        return set()

    from apps.permissions.models import ManagementScope

    branch_id = branch.id if hasattr(branch, 'id') else branch
    explicit_user_ids = set(ManagementScope.objects.filter(
        user__in=users,
    ).values_list('user_id', flat=True))
    explicitly_local = set(ManagementScope.objects.filter(
        user__in=users, branch_id=branch_id,
    ).values_list('user_id', flat=True))
    default_local = {
        user.id for user in users
        if user.id not in explicit_user_ids and user.branch_id == branch_id
    }
    return explicitly_local | default_local


def _upper_user_ids(users, branch):
    if branch is None:
        return set()

    from apps.organizations.models import Branch
    from apps.permissions.models import ManagementScope

    branch_id = branch.id if hasattr(branch, 'id') else branch
    branch_obj = Branch.objects.select_related('team', 'team__region').filter(
        pk=branch_id,
    ).first()
    if branch_obj is None:
        return set()
    return set(ManagementScope.objects.filter(user__in=users).filter(
        Q(is_all_data=True)
        | Q(team_id=branch_obj.team_id)
        | Q(region_id=branch_obj.team.region_id)
    ).values_list('user_id', flat=True))


def _users_with_operation_access(branch, code, include_admin=True):
    from apps.users.models import User
    from apps.organizations.models import Branch
    from apps.permissions.scope import resolve_user_scope

    if branch is not None and not hasattr(branch, 'id'):
        by_id = Branch.objects.filter(pk=branch).first()
        branch = by_id or Branch.objects.filter(name=str(branch)).first()

    q = Q(operation_grants__code=code)
    if include_admin:
        q |= Q(role='admin')
    candidates = User.objects.filter(q, status='active').distinct()
    return [user for user in candidates if _covers_branch(user, branch)]


def get_transfer_approvers(branch, action_type):
    """Return users who may approve a document for notifications/list hints.

    Approval eligibility itself is evaluated by ``is_transfer_approver`` using
    the creator, role, and current scope. This helper keeps notifications
    useful without making a stored per-document approver list authoritative.
    """
    code = transfer_permission_code(action_type, 'approve')
    if not code:
        return []

    candidates = _users_with_operation_access(branch, code)
    return [
        user for user in candidates
        if user.role in ('leader', 'director', 'admin') and user.can(code)
    ]


def get_transfer_approvers_for_document(transfer):
    """Return the live role/scope approvers for a pending document.

    The creator-level manager rule is document-specific, so it cannot be
    represented by a branch-only approver list. Resolve candidates from the
    approval grant and reuse the same predicate as the list/action checks.
    """
    branch = transfer.业务分公司
    if branch is None and transfer.业务分公司名:
        from apps.organizations.models import Branch
        branch = Branch.objects.filter(name=transfer.业务分公司名).first()
    code = transfer_permission_code(transfer.action_type, 'approve')
    if not code:
        return []
    candidates = _users_with_operation_access(branch, code)
    return [user for user in candidates if is_transfer_approver(user, transfer)]


def is_transfer_approver(user, transfer):
    if user.role == 'admin':
        return True
    code = transfer_permission_code(transfer.action_type, 'approve')
    view_code = transfer_permission_code(transfer.action_type, 'view')
    if not code or not user.can(code) or (view_code and not user.can(view_code)):
        return False
    branch = transfer.业务分公司
    if branch is None and transfer.业务分公司名:
        from apps.organizations.models import Branch
        branch = Branch.objects.filter(name=transfer.业务分公司名).first()
    if not _covers_branch(user, branch):
        return False
    if user.role == 'manager':
        return transfer.created_by_id == user.id
    return user.role in ('leader', 'director')


def get_transfer_inbound_rejectors(branch):
    return [
        user for user in _users_with_operation_access(
            branch, 'edit_transfer', include_admin=False,
        )
        if user.can('edit_transfer')
    ]


def is_transfer_inbound_rejector_for_branch(user, branch):
    if user.role == 'admin':
        return True
    return any(
        rejector.id == user.id
        for rejector in get_transfer_inbound_rejectors(branch)
    )


def is_transfer_inbound_rejector(user, transfer):
    branch = transfer.to_branch
    if branch is None and transfer.调入分公司:
        from apps.organizations.models import Branch
        branch = Branch.objects.filter(name=transfer.调入分公司).first()
    return is_transfer_inbound_rejector_for_branch(user, branch)


def get_upper_approval_report_recipients(branch):
    """Return upper-scope report readers and system admins for known branches."""
    if branch is None:
        return []

    candidates = _users_with_operation_access(branch, 'view_approval_reports')
    upper_ids = _upper_user_ids(candidates, branch)
    # System admins have implicit all-data scope, even without a ManagementScope row.
    upper_ids.update(user.id for user in candidates if user.role == 'admin')
    return [user for user in candidates if user.id in upper_ids]
