"""Versioned, account-materialized permission baselines for ordinary positions."""

from copy import deepcopy

from django.db import transaction

POSITION_BASELINE_VERSION = 'v1'

_LEADER_BASELINE = (
    'view_dashboard',
    'view_notifications',
    'view_approval_reports',
    'view_reports',
    'view_categories',
    'view_departments',
    'view_suppliers',
    'view_users',
    'view_organizations',
    'view_asset_ledger',
    'view_instances',
    'edit_instances',
    'change_instance_assignee',
    'print_instance_label',
    'view_purchase',
    'edit_purchase',
    'delete_purchase_draft',
    'approve_purchase',
    'view_assignment',
    'edit_assignment',
    'delete_assignment_draft',
    'approve_assignment',
    'view_transfer',
    'edit_transfer',
    'delete_transfer_draft',
    'approve_internal_transfer',
    'view_recovery',
    'view_recovery_ledger',
    'edit_recovery',
    'delete_recovery_draft',
    'approve_recovery',
    'view_inventory',
    'edit_inventory',
    'review_inventory',
)

POSITION_BASELINE_CONFIG = {
    'version': POSITION_BASELINE_VERSION,
    'roles': {
        # leader: 行政组长; director: 大区负责人; manager: 分公司行政
        'leader': list(_LEADER_BASELINE),
        'director': sorted({*_LEADER_BASELINE, 'edit_users', 'edit_organizations', 'delete_organizations'}),
        'manager': sorted(set(_LEADER_BASELINE) - {'approve_recovery', 'review_inventory'}),
    },
}


def _normalized_config(config):
    roles = config.get('roles') or {}
    return {
        'version': str(config.get('version') or ''),
        'roles': {
            str(role): sorted({str(code) for code in codes})
            for role, codes in roles.items()
        },
    }


def get_active_baseline_config(*, lock=False):
    """Return the confirmed configuration, falling back to the bundled first version."""
    from .models import PositionBaselineState

    query = PositionBaselineState.objects
    if lock:
        query = query.select_for_update()
    state = query.filter(pk=1).first()
    if state and state.version and state.baseline_config:
        return _normalized_config(state.baseline_config)
    return deepcopy(POSITION_BASELINE_CONFIG)


def get_role_baseline(role, config=None):
    config = config or get_active_baseline_config()
    return set(config.get('roles', {}).get(role, ()))


def validate_baseline_config(config):
    from .operations import OPERATION_CATALOG, missing_operation_prerequisites

    normalized = _normalized_config(config)
    if not normalized['version']:
        raise ValueError('岗位权限基线版本不能为空')
    if set(normalized['roles']) != {'manager', 'leader', 'director'}:
        raise ValueError('岗位基线必须明确包含分公司行政、行政组长和大区负责人三个普通岗位')
    catalog_codes = {item['code'] for item in OPERATION_CATALOG}
    for role, codes in normalized['roles'].items():
        unknown = set(codes) - catalog_codes
        if unknown:
            raise ValueError(f'{role} 岗位基线包含目录外权限：{", ".join(sorted(unknown))}')
    if {'view_reconciliation', 'view_audit_logs'} & set().union(
        *(set(codes) for role, codes in normalized['roles'].items())
    ):
        raise ValueError('普通岗位基线不得包含查看对账或查看审计日志')
    for role, codes in normalized['roles'].items():
        missing = missing_operation_prerequisites(codes)
        if missing:
            raise ValueError(f'{role} 岗位基线缺少操作前置权限')
    return normalized


def _upsert_assignment(user, config, codes=None):
    from .models import PositionBaselineAssignment

    baseline_codes = sorted(codes if codes is not None else get_role_baseline(user.role, config))
    PositionBaselineAssignment.objects.update_or_create(
        user=user,
        defaults={
            'version': config['version'],
            'role': user.role,
            'baseline_codes': baseline_codes,
        },
    )
    return set(baseline_codes)


def replace_active_grants(user, codes):
    """Replace current-catalog grants while preserving unrecognized historical rows."""
    from .models import OperationGrant
    from .operations import OPERATION_CATALOG

    catalog_codes = {item['code'] for item in OPERATION_CATALOG}
    desired = set(codes) & catalog_codes
    user.operation_grants.filter(code__in=catalog_codes).delete()
    OperationGrant.objects.bulk_create([
        OperationGrant(user=user, code=code) for code in sorted(desired)
    ])


def reset_user_to_position_baseline(user, *, config=None):
    """Apply a new role baseline and clear personal permission exceptions."""
    from .models import PositionBaselineAssignment, PositionPermissionOverride

    config = config or get_active_baseline_config()
    if user.role == 'admin':
        PositionBaselineAssignment.objects.filter(user=user).delete()
        PositionPermissionOverride.objects.filter(user=user).delete()
        return set()

    baseline = get_role_baseline(user.role, config)
    replace_active_grants(user, baseline)
    PositionPermissionOverride.objects.filter(user=user).delete()
    _upsert_assignment(user, config, baseline)
    return baseline


def synchronize_user_baseline(user, *, config=None):
    """Rebase an account while keeping its recorded personal additions/cancellations."""
    from .models import PositionBaselineAssignment, PositionPermissionOverride
    from .operations import OPERATION_CATALOG

    config = config or get_active_baseline_config()
    if user.role == 'admin':
        return set()

    catalog_codes = {item['code'] for item in OPERATION_CATALOG}
    current_codes = set(user.operation_grants.filter(code__in=catalog_codes).values_list('code', flat=True))
    baseline = get_role_baseline(user.role, config)
    assignment = PositionBaselineAssignment.objects.filter(user=user).first()
    additions = set(PositionPermissionOverride.objects.filter(
        user=user, effect=PositionPermissionOverride.GRANT,
    ).values_list('code', flat=True))
    cancellations = set(PositionPermissionOverride.objects.filter(
        user=user, effect=PositionPermissionOverride.REVOKE,
    ).values_list('code', flat=True))

    if assignment is None:
        additions.update(current_codes - baseline)
        desired = baseline | additions
    else:
        desired = (baseline | additions) - cancellations

    replace_active_grants(user, desired)
    if assignment is None and additions:
        PositionPermissionOverride.objects.bulk_create([
            PositionPermissionOverride(user=user, code=code, effect=PositionPermissionOverride.GRANT)
            for code in sorted(additions)
        ], ignore_conflicts=True)
    _upsert_assignment(user, config, baseline)
    return desired


def record_user_permission_overrides(user, granted_codes):
    """Persist the selected effective grant set as deltas from its role snapshot."""
    from .models import PositionBaselineAssignment, PositionPermissionOverride
    from .operations import OPERATION_CATALOG

    if user.role == 'admin':
        return
    catalog_codes = {item['code'] for item in OPERATION_CATALOG}
    grants = set(granted_codes) & catalog_codes
    assignment = PositionBaselineAssignment.objects.filter(user=user).first()
    if assignment is None:
        baseline = get_role_baseline(user.role)
        _upsert_assignment(user, get_active_baseline_config(), baseline)
    else:
        baseline = set(assignment.baseline_codes)

    PositionPermissionOverride.objects.filter(user=user).delete()
    PositionPermissionOverride.objects.bulk_create([
        PositionPermissionOverride(user=user, code=code, effect=PositionPermissionOverride.GRANT)
        for code in sorted(grants - baseline)
    ] + [
        PositionPermissionOverride(user=user, code=code, effect=PositionPermissionOverride.REVOKE)
        for code in sorted(baseline - grants)
    ])


def plan_user_baseline(user, target_config):
    """Return the grants and review codes that a baseline confirmation would produce."""
    from .models import PositionBaselineAssignment, PositionPermissionOverride
    from .operations import OPERATION_CATALOG

    catalog_codes = {item['code'] for item in OPERATION_CATALOG}
    current_codes = set(user.operation_grants.values_list('code', flat=True))
    current_valid = current_codes & catalog_codes
    legacy_codes = current_codes - catalog_codes
    target_base = get_role_baseline(user.role, target_config)
    assignment = PositionBaselineAssignment.objects.filter(user=user).first()

    if assignment is None:
        # Existing explicit grants are retained during the first baseline sync.
        desired = current_valid | target_base
    else:
        additions = set(PositionPermissionOverride.objects.filter(
            user=user, effect=PositionPermissionOverride.GRANT,
        ).values_list('code', flat=True))
        cancellations = set(PositionPermissionOverride.objects.filter(
            user=user, effect=PositionPermissionOverride.REVOKE,
        ).values_list('code', flat=True))
        desired = (target_base | additions) - cancellations

    return {
        'current': current_valid,
        'desired': desired,
        'added': desired - current_valid,
        'removed': current_valid - desired,
        'legacy': legacy_codes,
        'target_baseline': target_base,
        'assignment_missing': assignment is None,
    }


@transaction.atomic
def apply_user_baseline_plan(user, plan, config):
    """Persist a precomputed plan after the caller has locked and revalidated it."""
    from .models import PositionBaselineAssignment, PositionPermissionOverride
    from .operations import OPERATION_CATALOG

    replace_active_grants(user, plan['desired'])
    if plan['assignment_missing']:
        PositionPermissionOverride.objects.bulk_create([
            PositionPermissionOverride(user=user, code=code, effect=PositionPermissionOverride.GRANT)
            for code in sorted(plan['current'] - plan['target_baseline'])
        ], ignore_conflicts=True)
    _upsert_assignment(user, config, plan['target_baseline'])
