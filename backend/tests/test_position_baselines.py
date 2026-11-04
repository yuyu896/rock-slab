import pytest
from rest_framework import status

from apps.permissions.models import (
    ManagementScope,
    OperationGrant,
    PositionBaselineAssignment,
    PositionBaselineState,
    PositionPermissionOverride,
)
from apps.permissions.position_baselines import POSITION_BASELINE_CONFIG, get_role_baseline
from conftest import _client_for


def _operation_codes(user):
    return set(user.operation_grants.values_list('code', flat=True))


def _create_user(client, *, phone, role='manager', branch=None):
    payload = {
        'phone': phone,
        'name': f'基线测试{phone[-4:]}',
        'password': 'test123456',
        'role': role,
        'status': 'active',
    }
    if branch is not None:
        payload['branch'] = str(branch.id)
    response = client.post('/api/users/', payload, format='json')
    assert response.status_code == status.HTTP_201_CREATED, response.data
    from apps.users.models import User
    return User.objects.get(pk=response.data['id'])


def _save_authorization(client, user, operations, scope=None):
    return client.put(
        f'/api/permissions/users/{user.id}/authorization',
        {
            'operations': sorted(operations),
            'scope': scope or {'mode': 'default', 'nodes': []},
        },
        format='json',
    )


@pytest.mark.django_db
def test_confirmed_position_baselines_have_exact_sets_and_exclude_special_permissions(admin_user):
    leader = get_role_baseline('leader')
    director = get_role_baseline('director')
    manager = get_role_baseline('manager')

    assert len(leader) == 34
    assert director == leader | {'edit_users', 'edit_organizations', 'delete_organizations'}
    assert len(director) == 37
    assert manager == leader - {'approve_recovery', 'review_inventory'}
    assert len(manager) == 32
    assert not ({'view_reconciliation', 'view_audit_logs'} & (leader | director | manager))
    assert admin_user.can('view_audit_logs') is True


@pytest.mark.django_db
def test_new_employee_receives_baseline_in_account_grants(authenticated_client, branch):
    from apps.permissions.scope import resolve_user_scope

    user = _create_user(authenticated_client, phone='13690001001', role='leader', branch=branch)

    assert _operation_codes(user) == get_role_baseline('leader')
    assignment = PositionBaselineAssignment.objects.get(user=user)
    assert assignment.version == POSITION_BASELINE_CONFIG['version']
    assert set(assignment.baseline_codes) == get_role_baseline('leader')
    assert not user.management_scopes.exists()
    assert resolve_user_scope(user).branches == {branch.id}
    assert 'view_reconciliation' not in _operation_codes(user)
    assert 'view_audit_logs' not in _operation_codes(user)


@pytest.mark.django_db
def test_position_template_endpoint_returns_versioned_baseline_catalog(authenticated_client):
    response = authenticated_client.get('/api/permissions/position-templates')

    assert response.status_code == status.HTTP_200_OK
    rows = {row['role']: row for row in response.data}
    assert set(rows) == {'leader', 'director', 'manager'}
    assert rows['leader']['version'] == POSITION_BASELINE_CONFIG['version']
    assert set(rows['manager']['operations']) == get_role_baseline('manager')


@pytest.mark.django_db
def test_role_change_resets_business_permissions_and_scope_to_new_role_baseline(
    authenticated_client, branch, second_branch,
):
    user = _create_user(authenticated_client, phone='13690001002', role='manager', branch=branch)
    OperationGrant.objects.create(user=user, code='view_permission_matrix')
    PositionPermissionOverride.objects.create(user=user, code='view_permission_matrix', effect='grant')
    user.operation_grants.filter(code='view_recovery_ledger').delete()
    PositionPermissionOverride.objects.create(user=user, code='view_recovery_ledger', effect='revoke')
    ManagementScope.objects.create(user=user, branch=second_branch)

    response = authenticated_client.patch(
        f'/api/users/{user.id}', {'role': 'director'}, format='json',
    )
    user.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK, response.data
    assert _operation_codes(user) == get_role_baseline('director')
    assert not PositionPermissionOverride.objects.filter(user=user).exists()
    assignment = PositionBaselineAssignment.objects.get(user=user)
    assert assignment.role == 'director'
    assert set(assignment.baseline_codes) == get_role_baseline('director')
    assert not user.management_scopes.exists()
    from apps.permissions.scope import resolve_user_scope
    assert resolve_user_scope(user).branches == {branch.id}


@pytest.mark.django_db
def test_branch_change_preserves_business_permissions_and_resets_scope(
    authenticated_client, branch, second_branch,
):
    from apps.permissions.scope import resolve_user_scope

    user = _create_user(authenticated_client, phone='13690001003', role='manager', branch=branch)
    OperationGrant.objects.create(user=user, code='view_permission_matrix')
    PositionPermissionOverride.objects.create(user=user, code='view_permission_matrix', effect='grant')
    ManagementScope.objects.create(user=user, branch=second_branch)
    before = _operation_codes(user)

    response = authenticated_client.patch(
        f'/api/users/{user.id}', {'branch': str(second_branch.id)}, format='json',
    )
    user.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK, response.data
    assert _operation_codes(user) == before
    assert PositionPermissionOverride.objects.get(user=user, code='view_permission_matrix').effect == 'grant'
    assert not user.management_scopes.exists()
    assert resolve_user_scope(user).branches == {second_branch.id}


@pytest.mark.django_db
def test_initial_baseline_preview_is_read_only_and_confirm_merges_existing_grants_and_scope(
    authenticated_client, branch, second_branch,
):
    from apps.users.models import User

    user = User.objects.create_user(
        phone='13690001004', name='存量员工', password='x',
        role='manager', status='active', branch=branch,
    )
    OperationGrant.objects.create(user=user, code='view_permission_matrix')
    OperationGrant.objects.create(user=user, code='old_unmapped_operation')
    ManagementScope.objects.create(user=user, branch=second_branch)
    before_grants = _operation_codes(user)

    preview_response = authenticated_client.get('/api/permissions/position-baselines/preview')
    assert preview_response.status_code == status.HTTP_200_OK
    preview = preview_response.data
    row = next(item for item in preview['employees'] if item['user'] == str(user.id))
    assert row['added']
    assert row['legacy_codes'] == ['old_unmapped_operation']
    assert row['scope_preserved'] is True
    user.refresh_from_db()
    assert _operation_codes(user) == before_grants
    assert user.management_scopes.filter(branch=second_branch).exists()

    OperationGrant.objects.create(user=user, code='view_reconciliation')
    stale_apply = authenticated_client.post('/api/permissions/position-baselines/apply', {
        'expected_from_version': preview['from_version'],
        'preview_token': preview['preview_token'],
    }, format='json')
    assert stale_apply.status_code == status.HTTP_409_CONFLICT
    assert not PositionBaselineAssignment.objects.filter(user=user).exists()

    fresh_preview = authenticated_client.get('/api/permissions/position-baselines/preview').data
    apply_response = authenticated_client.post('/api/permissions/position-baselines/apply', {
        'expected_from_version': fresh_preview['from_version'],
        'preview_token': fresh_preview['preview_token'],
    }, format='json')

    assert apply_response.status_code == status.HTTP_200_OK, apply_response.data
    user.refresh_from_db()
    expected = get_role_baseline('manager') | {'view_permission_matrix', 'view_reconciliation'}
    assert _operation_codes(user) == expected | {'old_unmapped_operation'}
    assert PositionBaselineAssignment.objects.get(user=user).version == POSITION_BASELINE_CONFIG['version']
    assert user.management_scopes.filter(branch=second_branch).exists()
    assert PositionBaselineState.objects.get(pk=1).version == POSITION_BASELINE_CONFIG['version']


@pytest.mark.django_db
def test_baseline_change_preview_confirm_preserves_personal_additions_and_cancellations(
    authenticated_client, monkeypatch,
):
    import apps.permissions.baseline_views as baseline_views

    user = _create_user(authenticated_client, phone='13690001005', role='manager')
    personal = get_role_baseline('manager') - {'view_recovery_ledger'}
    personal.add('view_permission_matrix')
    saved = _save_authorization(authenticated_client, user, personal)
    assert saved.status_code == status.HTTP_200_OK, saved.data
    assert PositionPermissionOverride.objects.get(user=user, code='view_recovery_ledger').effect == 'revoke'
    assert PositionPermissionOverride.objects.get(user=user, code='view_permission_matrix').effect == 'grant'

    new_manager = (get_role_baseline('manager') - {'view_reports'}) | {'edit_users'}
    target = {
        'version': 'v2-test',
        'roles': {
            role: sorted(new_manager if role == 'manager' else codes)
            for role, codes in POSITION_BASELINE_CONFIG['roles'].items()
        },
    }
    monkeypatch.setattr(baseline_views, 'POSITION_BASELINE_CONFIG', target)
    preview = authenticated_client.get('/api/permissions/position-baselines/preview')
    assert preview.status_code == status.HTTP_200_OK
    row = next(item for item in preview.data['employees'] if item['user'] == str(user.id))
    assert {item['code'] for item in row['added']} == {'edit_users'}
    assert {item['code'] for item in row['removed']} == {'view_reports'}

    applied = authenticated_client.post('/api/permissions/position-baselines/apply', {
        'expected_from_version': preview.data['from_version'],
        'preview_token': preview.data['preview_token'],
    }, format='json')
    assert applied.status_code == status.HTTP_200_OK, applied.data
    user.refresh_from_db()

    assert _operation_codes(user) == (new_manager | {'view_permission_matrix'}) - {'view_recovery_ledger'}
    assert PositionPermissionOverride.objects.get(user=user, code='view_recovery_ledger').effect == 'revoke'
    assert PositionPermissionOverride.objects.get(user=user, code='view_permission_matrix').effect == 'grant'
    assignment = PositionBaselineAssignment.objects.get(user=user)
    assert assignment.version == 'v2-test'
    assert set(assignment.baseline_codes) == new_manager


@pytest.mark.django_db
def test_reactivation_rebases_current_role_and_preserves_personal_changes_and_scope(
    authenticated_client,
):
    user = _create_user(authenticated_client, phone='13690001006', role='manager')
    granted = get_role_baseline('manager') - {'view_recovery_ledger'}
    granted.add('view_permission_matrix')
    assert _save_authorization(
        authenticated_client, user, granted,
        {'mode': 'all', 'nodes': []},
    ).status_code == status.HTTP_200_OK

    new_manager = (get_role_baseline('manager') - {'view_reports'}) | {'edit_users'}
    new_config = {
        'version': 'v2-reactivation',
        'roles': {
            role: sorted(new_manager if role == 'manager' else codes)
            for role, codes in POSITION_BASELINE_CONFIG['roles'].items()
        },
    }
    state, _ = PositionBaselineState.objects.get_or_create(
        pk=1,
        defaults={
            'version': POSITION_BASELINE_CONFIG['version'],
            'baseline_config': POSITION_BASELINE_CONFIG,
        },
    )
    state.version = new_config['version']
    state.baseline_config = new_config
    state.save()

    assert authenticated_client.patch(
        f'/api/users/{user.id}', {'status': 'inactive'}, format='json',
    ).status_code == status.HTTP_200_OK
    inactive_grants = _operation_codes(user)
    assert inactive_grants == granted
    assert user.management_scopes.filter(is_all_data=True).exists()
    assert authenticated_client.patch(
        f'/api/users/{user.id}', {'status': 'active'}, format='json',
    ).status_code == status.HTTP_200_OK
    user.refresh_from_db()

    assert user.is_active is True
    assert _operation_codes(user) == (new_manager | {'view_permission_matrix'}) - {'view_recovery_ledger'}
    assert _operation_codes(user) != inactive_grants
    assert PositionPermissionOverride.objects.get(user=user, code='view_recovery_ledger').effect == 'revoke'
    assert PositionPermissionOverride.objects.get(user=user, code='view_permission_matrix').effect == 'grant'
    assert user.management_scopes.filter(is_all_data=True).exists()
    assert PositionBaselineAssignment.objects.get(user=user).version == new_config['version']


@pytest.mark.django_db
def test_scope_only_update_for_inactive_user_without_baseline_does_not_record_revocations(
    authenticated_client, branch,
):
    from apps.users.models import User

    user = User.objects.create_user(
        phone='13690001007', name='停用员工', password='x',
        role='manager', status='inactive', is_active=False, branch=branch,
    )
    OperationGrant.objects.create(user=user, code='view_permission_matrix')

    response = _save_authorization(
        authenticated_client,
        user,
        {'view_permission_matrix'},
        {'mode': 'custom', 'nodes': [{'type': 'branch', 'id': str(branch.id)}]},
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    assert not PositionBaselineAssignment.objects.filter(user=user).exists()
    assert not PositionPermissionOverride.objects.filter(user=user).exists()

    reactivated = authenticated_client.patch(
        f'/api/users/{user.id}', {'status': 'active'}, format='json',
    )

    assert reactivated.status_code == status.HTTP_200_OK, reactivated.data
    user.refresh_from_db()
    assert user.is_active is True
    assert _operation_codes(user) == get_role_baseline('manager') | {'view_permission_matrix'}
    assert PositionPermissionOverride.objects.filter(
        user=user, code='view_permission_matrix', effect='grant',
    ).exists()
    assert not PositionPermissionOverride.objects.filter(
        user=user, effect='revoke',
    ).exists()
    assert PositionBaselineAssignment.objects.get(user=user).version == POSITION_BASELINE_CONFIG['version']


@pytest.mark.django_db
def test_position_baseline_preview_is_admin_only(staff_user):
    response = _client_for(staff_user).get('/api/permissions/position-baselines/preview')

    assert response.status_code == status.HTTP_403_FORBIDDEN
