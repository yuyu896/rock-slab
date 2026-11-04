import json

import pytest
from django.core.management import call_command, CommandError

from apps.permissions.granular_migration import build_migration_plan
from apps.permissions.models import ManagementScope, OperationGrant
from apps.users.models import User


def _user(phone, name, branch=None, role='manager'):
    return User.objects.create_user(
        phone=phone, name=name, password='test123456', role=role, branch=branch,
    )


@pytest.fixture
def command_admin(branch):
    return _user('13919999999', '权限迁移操作人', branch=branch, role='admin')


def _account(plan, user):
    return next(row for row in plan['accounts'] if row['user_id'] == str(user.id))


def _write_plan(path, plan):
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')


@pytest.mark.django_db
def test_plan_does_not_expand_legacy_approval_or_derive_from_role(branch):
    user = _user('13910000001', '授权用户', branch=branch, role='manager')
    empty_user = _user('13910000009', '无授权用户', branch=branch, role='manager')
    grant = OperationGrant.objects.create(user=user, code='approve_transfer')

    first = build_migration_plan()
    first_account = _account(first, user)
    assert _account(first, empty_user)['after_grants'] == []
    approval = next(row for row in first_account['grant_mappings'] if row['grant_id'] == str(grant.id))
    assert approval['state'] == 'unmapped'
    assert approval['to'] == []
    assert first_account['after_grants'] == []
    assert first_account['unmapped_codes_retained'] == ['approve_transfer']

    user.role = 'leader'
    user.save(update_fields=['role'])
    second_account = _account(build_migration_plan(), user)
    second_approval = next(row for row in second_account['grant_mappings'] if row['grant_id'] == str(grant.id))
    assert second_approval['state'] == 'unmapped'
    assert second_approval['to'] == []
    assert second_account['after_grants'] == []
    assert OperationGrant.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_manage_dictionary_maps_to_category_operations(branch):
    user = _user('13910000011', '品目权限用户', branch=branch)
    grant = OperationGrant.objects.create(user=user, code='manage_dictionary')

    account = _account(build_migration_plan(), user)
    mapping = next(row for row in account['grant_mappings'] if row['grant_id'] == str(grant.id))

    assert mapping['state'] == 'mapped'
    assert set(mapping['to']) == {'view_categories', 'edit_categories'}
    assert account['after_grants'] == sorted(mapping['to'])


@pytest.mark.django_db
def test_management_grants_map_to_merged_edit_operations(branch):
    user = _user('13910000012', '基础维护用户', branch=branch)
    grants = [
        OperationGrant.objects.create(user=user, code='manage_users'),
        OperationGrant.objects.create(user=user, code='manage_organizations'),
        OperationGrant.objects.create(user=user, code='manage_departments'),
        OperationGrant.objects.create(user=user, code='manage_suppliers'),
    ]

    account = _account(build_migration_plan(), user)
    mappings = {row['from']: row for row in account['grant_mappings']}

    assert set(mappings['manage_users']['to']) == {'view_users', 'edit_users'}
    assert mappings['manage_organizations']['state'] == 'partially_mapped'
    assert set(mappings['manage_organizations']['to']) == {
        'view_organizations', 'edit_organizations', 'delete_organizations',
    }
    assert set(mappings['manage_organizations']['unmapped_targets']) == {
        'view_departments', 'edit_departments',
    }
    assert set(mappings['manage_departments']['to']) == {'view_departments', 'edit_departments'}
    assert set(mappings['manage_suppliers']['to']) == {'view_suppliers', 'edit_suppliers'}
    assert all(grant.code in account['before_grants'] for grant in grants)


@pytest.mark.django_db
def test_partial_organization_mapping_preserves_department_review_until_apply_confirmation(
    branch, tmp_path, command_admin,
):
    user = _user('13910000015', '组织权限用户', branch=branch)
    grant = OperationGrant.objects.create(user=user, code='manage_organizations')
    plan = build_migration_plan()
    account = _account(plan, user)
    mapping = next(row for row in account['grant_mappings'] if row['grant_id'] == str(grant.id))
    organization_codes = {
        'view_organizations', 'edit_organizations', 'delete_organizations',
    }
    department_codes = {'view_departments', 'edit_departments'}

    assert mapping['state'] == 'partially_mapped'
    assert set(mapping['to']) == organization_codes
    assert set(mapping['unmapped_targets']) == department_codes
    assert account['after_grants'] == sorted(organization_codes)
    assert account['unmapped_codes_retained'] == ['manage_organizations']
    assert plan['summary']['partially_mapped_grant_count'] == 1
    assert plan['summary']['unmapped_grant_count'] == 0
    assert plan['summary']['pending_review_grant_count'] == 1
    assert plan['partially_mapped_grants'][0]['unmapped_targets'] == mapping['unmapped_targets']

    plan_path = tmp_path / 'plan.json'
    snapshot_path = tmp_path / 'snapshot.json'
    _write_plan(plan_path, plan)
    apply_args = [
        'migrate_granular_permissions', '--apply', '--plan', str(plan_path),
        '--confirm', plan['plan_id'], '--snapshot', str(snapshot_path),
        '--actor-id', str(command_admin.id),
    ]
    with pytest.raises(CommandError, match='--accept-unmapped'):
        call_command(*apply_args)
    assert OperationGrant.objects.filter(pk=grant.pk).exists()
    assert not snapshot_path.exists()

    call_command(*apply_args, '--accept-unmapped')
    assert OperationGrant.objects.filter(pk=grant.pk, code='manage_organizations').exists()
    assert set(OperationGrant.objects.filter(user=user).values_list('code', flat=True)) == (
        organization_codes | {'manage_organizations'}
    )
    assert not OperationGrant.objects.filter(user=user, code__in=department_codes).exists()
    call_command('migrate_granular_permissions', '--verify-snapshot', str(snapshot_path))

    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    call_command(
        'migrate_granular_permissions', '--restore-snapshot', str(snapshot_path),
        '--confirm-restore', snapshot['snapshot_id'], '--actor-id', str(command_admin.id),
    )
    assert list(OperationGrant.objects.filter(user=user).values_list('code', flat=True)) == [
        'manage_organizations',
    ]


@pytest.mark.django_db
def test_admin_grants_are_reported_as_builtin_and_preview_is_read_only(branch):
    admin = _user('13910000010', '管理员', branch=branch, role='admin')
    grant = OperationGrant.objects.create(user=admin, code='manage_assets')

    account = _account(build_migration_plan(), admin)

    assert account['automatic_admin_all'] is True
    assert account['after_grants'] == ['全部（系统管理员内置）']
    assert account['grant_mappings'][0]['state'] == 'admin_builtin'
    assert OperationGrant.objects.filter(pk=grant.pk, code='manage_assets').exists()


@pytest.mark.django_db
def test_admin_grant_rows_are_cleared_when_plan_is_applied(branch, tmp_path, command_admin):
    admin = _user('13910000012', '管理员', branch=branch, role='admin')
    grant = OperationGrant.objects.create(user=admin, code='manage_assets')
    scope = ManagementScope.objects.create(user=admin, branch=branch)
    plan = build_migration_plan()
    assert _account(plan, admin)['scope']['redundant_rows_to_remove'] == 1
    plan_path = tmp_path / 'plan.json'
    snapshot_path = tmp_path / 'snapshot.json'
    _write_plan(plan_path, plan)

    call_command(
        'migrate_granular_permissions', '--apply', '--plan', str(plan_path),
        '--confirm', plan['plan_id'], '--snapshot', str(snapshot_path),
        '--actor-id', str(command_admin.id),
    )

    assert not OperationGrant.objects.filter(pk=grant.pk).exists()
    assert not ManagementScope.objects.filter(pk=scope.pk).exists()
    call_command('migrate_granular_permissions', '--verify-snapshot', str(snapshot_path))
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    call_command(
        'migrate_granular_permissions', '--restore-snapshot', str(snapshot_path),
        '--confirm-restore', snapshot['snapshot_id'], '--actor-id', str(command_admin.id),
    )
    assert OperationGrant.objects.filter(pk=grant.pk, code='manage_assets').exists()


@pytest.mark.django_db
def test_plan_reports_unmappable_grants_and_scope_before_after(branch, region):
    user = _user('13910000002', '范围用户', branch=branch)
    OperationGrant.objects.create(user=user, code='manage_assets')
    region.manager = user
    region.save(update_fields=['manager'])

    plan = build_migration_plan()
    account = _account(plan, user)
    assert account['before_grants'] == ['manage_assets']
    assert account['after_grants'] == []
    assert account['unmapped_codes_retained'] == ['manage_assets']
    assert account['scope']['before']['branches'] == [
        {'id': str(branch.id), 'name': branch.name},
    ]
    assert account['scope']['after']['branches'] == [
        {'id': str(branch.id), 'name': branch.name},
    ]
    assert account['scope']['after'] == account['scope']['before']
    assert account['scope']['appointment_scopes_to_preserve'][0]['type'] == 'region'
    assert plan['summary']['appointment_scope_count'] == 1
    assert plan['summary']['unmapped_grant_count'] == 1
    assert '绝不按岗位或岗位模板补发权限' in plan['provenance_warning']


@pytest.mark.django_db
def test_apply_materializes_current_appointments_and_restore_removes_them(
    branch, tmp_path, command_admin,
):
    user = _user('13910000014', '任命范围用户', branch=branch)
    region = branch.team.region
    team = branch.team
    region.manager = user
    region.save(update_fields=['manager'])
    team.leader = user
    team.save(update_fields=['leader'])
    branch.manager = user
    branch.save(update_fields=['manager'])

    plan = build_migration_plan()
    account = _account(plan, user)
    appointment_scopes = account['scope']['appointment_scopes_to_preserve']
    assert {scope['type'] for scope in appointment_scopes} == {'region', 'team', 'branch'}
    assert account['scope']['after'] == account['scope']['before']
    assert all(not scope['already_explicit'] for scope in appointment_scopes)

    plan_path = tmp_path / 'plan.json'
    snapshot_path = tmp_path / 'snapshot.json'
    _write_plan(plan_path, plan)
    call_command(
        'migrate_granular_permissions', '--apply', '--plan', str(plan_path),
        '--confirm', plan['plan_id'], '--snapshot', str(snapshot_path),
        '--actor-id', str(command_admin.id),
    )

    assert ManagementScope.objects.filter(user=user, region=region).exists()
    assert ManagementScope.objects.filter(user=user, team=team).exists()
    assert ManagementScope.objects.filter(user=user, branch=branch).exists()
    from apps.audit.models import AuditLog
    assert AuditLog.objects.filter(
        user=command_admin, resource_type='user_authorization', resource_id=user.id,
        description__contains='旧权限目录迁移已应用',
    ).exists()

    region.manager = None
    region.save(update_fields=['manager'])
    team.leader = None
    team.save(update_fields=['leader'])
    branch.manager = None
    branch.save(update_fields=['manager'])
    after_appointment_change = _account(build_migration_plan(), user)['scope']
    assert after_appointment_change['appointment_scopes_to_preserve'] == []
    assert after_appointment_change['before'] == account['scope']['after']
    assert after_appointment_change['after'] == account['scope']['after']

    call_command('migrate_granular_permissions', '--verify-snapshot', str(snapshot_path))
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    call_command(
        'migrate_granular_permissions', '--restore-snapshot', str(snapshot_path),
        '--confirm-restore', snapshot['snapshot_id'], '--actor-id', str(command_admin.id),
    )
    assert not ManagementScope.objects.filter(user=user).exists()
    assert AuditLog.objects.filter(
        user=command_admin, resource_type='user_authorization', resource_id=user.id,
        description__contains='旧权限目录迁移已从快照恢复',
    ).exists()


@pytest.mark.django_db
def test_legacy_adjust_ledger_grant_requires_per_user_permission_review(branch):
    user = _user('13910000013', 'Legacy ledger adjustment user', branch=branch)
    grant = OperationGrant.objects.create(user=user, code='adjust_ledger')

    plan = build_migration_plan()
    account = _account(plan, user)
    mapping = next(
        row for row in account['grant_mappings'] if row['grant_id'] == str(grant.id)
    )

    assert mapping['state'] == 'unmapped'
    assert mapping['to'] == []
    assert account['after_grants'] == []
    assert account['unmapped_codes_retained'] == ['adjust_ledger']
    assert '手工创建台账调整单' in mapping['reason']
    assert '台账导入流程也接受该权限' in mapping['reason']
    assert not user.can('import_asset_ledger')
    assert not user.can('adjust_asset_ledger')
    assert plan['summary']['unmapped_grant_count'] == 1


@pytest.mark.django_db
def test_default_branch_scope_is_previewed_and_dry_run_does_not_write(branch, tmp_path):
    user = _user('13910000003', '默认范围用户', branch=branch)
    OperationGrant.objects.create(user=user, code='approve_inventory')
    before_grants = list(OperationGrant.objects.values_list('user_id', 'code'))
    before_scopes = list(ManagementScope.objects.values_list('id', 'user_id'))

    output = tmp_path / 'plan.json'
    call_command('migrate_granular_permissions', '--output', str(output))

    report = json.loads(output.read_text(encoding='utf-8'))
    account = _account(report, user)
    assert account['scope']['before'] == {'all': False, 'branches': []}
    assert account['scope']['after']['branches'] == [{'id': str(branch.id), 'name': branch.name}]
    assert list(OperationGrant.objects.values_list('user_id', 'code')) == before_grants
    assert list(ManagementScope.objects.values_list('id', 'user_id')) == before_scopes


@pytest.mark.django_db
def test_read_only_preview_saves_pre_release_authorization_snapshot(branch, tmp_path):
    from apps.permissions.granular_migration import authorization_digest, validate_snapshot

    user = _user('13910000081', '只读快照用户', branch=branch)
    OperationGrant.objects.create(user=user, code='view_categories')
    ManagementScope.objects.create(user=user, branch=branch)
    before_digest = authorization_digest()
    output = tmp_path / 'permission-plan.json'
    snapshot_path = tmp_path / 'pre-release-snapshot.json'

    call_command(
        'migrate_granular_permissions',
        '--output', str(output),
        '--snapshot-output', str(snapshot_path),
    )

    plan = json.loads(output.read_text(encoding='utf-8'))
    snapshot_text = snapshot_path.read_text(encoding='utf-8')
    snapshot = json.loads(snapshot_text)
    assert plan['summary']['account_count'] >= 1
    assert snapshot['kind'] == 'pre_release_authorization'
    assert snapshot['expected_after_authorization_digest'] is None
    assert validate_snapshot(snapshot)
    assert user.name not in snapshot_text
    assert authorization_digest() == before_digest

    with pytest.raises(CommandError, match='迁移前差异复核'):
        call_command(
            'migrate_granular_permissions', '--verify-snapshot', str(snapshot_path),
        )


@pytest.mark.django_db
def test_snapshot_output_requires_plan_file_to_avoid_printing_personal_data():
    with pytest.raises(CommandError, match='不能输出到标准输出'):
        call_command('migrate_granular_permissions', '--snapshot-output', 'snapshot.json')


@pytest.mark.django_db
def test_apply_requires_confirmed_plan_and_snapshot_then_restores(branch, tmp_path, command_admin):
    user = _user('13910000004', '审批用户', branch=branch)
    grant = OperationGrant.objects.create(user=user, code='approve_inventory')
    OperationGrant.objects.create(user=user, code='view_inventory')
    scope = ManagementScope.objects.create(user=user, branch=branch)
    plan = build_migration_plan()
    plan_path = tmp_path / 'plan.json'
    snapshot_path = tmp_path / 'snapshot.json'
    _write_plan(plan_path, plan)

    with pytest.raises(CommandError, match='--plan、--confirm'):
        call_command(
            'migrate_granular_permissions', '--apply', '--plan', str(plan_path),
            '--actor-id', str(command_admin.id),
        )
    assert OperationGrant.objects.filter(pk=grant.pk).exists()
    assert not snapshot_path.exists()

    apply_args = [
        'migrate_granular_permissions', '--apply', '--plan', str(plan_path),
        '--confirm', plan['plan_id'], '--snapshot', str(snapshot_path),
        '--actor-id', str(command_admin.id),
    ]
    with pytest.raises(CommandError, match='--accept-unmapped'):
        call_command(*apply_args)
    with pytest.raises(CommandError, match='--preserve-scope-id'):
        call_command(*apply_args, '--accept-unmapped')
    assert OperationGrant.objects.filter(pk=grant.pk).exists()
    assert not snapshot_path.exists()

    call_command(
        *apply_args, '--accept-unmapped', '--preserve-scope-id', str(scope.id),
    )
    assert OperationGrant.objects.filter(user=user, code='approve_inventory').exists()
    assert OperationGrant.objects.filter(user=user, code='review_inventory').exists()
    assert ManagementScope.objects.filter(pk=scope.pk).exists()
    from apps.audit.models import AuditLog
    assert AuditLog.objects.filter(
        user=command_admin, resource_type='user_authorization', resource_id=user.id,
        description__contains='旧权限目录迁移已应用',
    ).exists()

    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    call_command('migrate_granular_permissions', '--verify-snapshot', str(snapshot_path))
    with pytest.raises(CommandError, match='--confirm-restore'):
        call_command(
            'migrate_granular_permissions', '--restore-snapshot', str(snapshot_path),
            '--actor-id', str(command_admin.id),
        )
    call_command(
        'migrate_granular_permissions', '--restore-snapshot', str(snapshot_path),
        '--confirm-restore', snapshot['snapshot_id'], '--actor-id', str(command_admin.id),
    )
    assert OperationGrant.objects.filter(pk=grant.pk, code='approve_inventory').exists()
    assert not OperationGrant.objects.filter(user=user, code='review_inventory').exists()
    assert ManagementScope.objects.filter(pk=scope.pk).exists()


@pytest.mark.django_db
def test_scope_migration_requires_per_record_decisions_and_restores_dropped_scope(
    branch, region, tmp_path, command_admin,
):
    user = _user('13910000011', '范围复核用户', branch=branch)
    keep_scope = ManagementScope.objects.create(user=user, branch=branch)
    drop_scope = ManagementScope.objects.create(user=user, region=region)
    region.manager = user
    region.save(update_fields=['manager'])
    plan = build_migration_plan()
    account = _account(plan, user)
    records = account['scope']['unclassified_records']
    assert {record['scope_id'] for record in records} == {
        str(keep_scope.id), str(drop_scope.id),
    }
    assert all(record['user_id'] == str(user.id) for record in records)
    assert all(record['data_range']['branches'] for record in records)
    assert next(
        scope for scope in account['scope']['appointment_scopes_to_preserve']
        if scope['type'] == 'region'
    )['already_explicit'] is True

    plan_path = tmp_path / 'plan.json'
    snapshot_path = tmp_path / 'snapshot.json'
    _write_plan(plan_path, plan)
    args = [
        'migrate_granular_permissions', '--apply', '--plan', str(plan_path),
        '--confirm', plan['plan_id'], '--snapshot', str(snapshot_path),
        '--actor-id', str(command_admin.id),
    ]

    with pytest.raises(CommandError, match='不存在这些 scope ID'):
        call_command(*args, '--preserve-scope-id', 'unknown-scope')
    with pytest.raises(CommandError, match='不能重复指定'):
        call_command(
            *args, '--preserve-scope-id', str(keep_scope.id),
            '--preserve-scope-id', str(keep_scope.id),
        )
    with pytest.raises(CommandError, match='同时选择保留和删除'):
        call_command(
            *args, '--preserve-scope-id', str(keep_scope.id),
            '--drop-scope-id', str(keep_scope.id),
            '--preserve-scope-id', str(drop_scope.id),
        )
    with pytest.raises(CommandError, match='未逐条选择'):
        call_command(*args, '--preserve-scope-id', str(keep_scope.id))
    assert not snapshot_path.exists()

    call_command(
        *args,
        '--preserve-scope-id', str(keep_scope.id),
        '--drop-scope-id', str(drop_scope.id),
    )
    assert ManagementScope.objects.filter(pk=keep_scope.pk).exists()
    assert not ManagementScope.objects.filter(pk=drop_scope.pk).exists()
    assert ManagementScope.objects.filter(user=user, region=region).exists()
    call_command('migrate_granular_permissions', '--verify-snapshot', str(snapshot_path))

    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    call_command(
        'migrate_granular_permissions', '--restore-snapshot', str(snapshot_path),
        '--confirm-restore', snapshot['snapshot_id'], '--actor-id', str(command_admin.id),
    )
    assert ManagementScope.objects.filter(pk=keep_scope.pk).exists()
    assert ManagementScope.objects.filter(user=user, region=region).exists()
    assert ManagementScope.objects.filter(user=user).count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize(
    'legacy_code', [
        'approve_transfer', 'manage_assets', 'manage_instances',
        'adjust_ledger', 'dispose_assets',
    ],
)
def test_unmapped_grant_requires_acknowledgement_and_is_preserved(
    branch, tmp_path, command_admin, legacy_code,
):
    user = _user('13910000005', '待复核用户', branch=branch)
    grant = OperationGrant.objects.create(user=user, code=legacy_code)
    plan = build_migration_plan()
    account = _account(plan, user)
    mapping = next(row for row in account['grant_mappings'] if row['grant_id'] == str(grant.id))
    assert mapping['state'] == 'unmapped'
    assert mapping['to'] == []
    assert account['after_grants'] == []
    assert account['unmapped_codes_retained'] == [legacy_code]
    if legacy_code == 'manage_instances':
        assert '直接更换使用人和部门' in mapping['reason']
        assert '不代表完整档案查看、导出或打印权限' in mapping['reason']
        assert not user.can('edit_instances')
        assert not user.can('change_instance_assignee')
        assert not user.can('view_instances')
        assert not user.can('print_instance_label')
    plan_path = tmp_path / 'plan.json'
    snapshot_path = tmp_path / 'snapshot.json'
    _write_plan(plan_path, plan)

    args = [
        'migrate_granular_permissions', '--apply', '--plan', str(plan_path),
        '--confirm', plan['plan_id'], '--snapshot', str(snapshot_path),
        '--actor-id', str(command_admin.id),
    ]
    with pytest.raises(CommandError, match='--accept-unmapped'):
        call_command(*args)
    assert OperationGrant.objects.filter(pk=grant.pk, code=legacy_code).exists()
    assert not snapshot_path.exists()

    call_command(*args, '--accept-unmapped')
    assert OperationGrant.objects.filter(pk=grant.pk, code=legacy_code).exists()
    assert not OperationGrant.objects.filter(
        user=user, code='adjust_asset_ledger',
    ).exists()
    assert not OperationGrant.objects.filter(
        user=user, code__in=('create_recovery', 'submit_recovery', 'approve_recovery'),
    ).exists()
    assert not OperationGrant.objects.filter(
        user=user,
        code__in=(
            'approve_purchase', 'approve_assignment', 'approve_return',
            'approve_internal_transfer', 'approve_recovery',
        ),
    ).exists()


@pytest.mark.django_db
def test_apply_rejects_tampered_or_stale_plan(branch, tmp_path, command_admin):
    user = _user('13910000006', '计划用户', branch=branch)
    OperationGrant.objects.create(user=user, code='approve_inventory')
    plan = build_migration_plan()
    plan_path = tmp_path / 'plan.json'
    snapshot_path = tmp_path / 'snapshot.json'

    tampered = json.loads(json.dumps(plan))
    tampered['accounts'][0]['after_grants'] = ['view_audit_logs']
    _write_plan(plan_path, tampered)
    with pytest.raises(CommandError, match='计划内容'):
        call_command(
            'migrate_granular_permissions', '--apply', '--plan', str(plan_path),
            '--confirm', plan['plan_id'], '--snapshot', str(snapshot_path),
            '--actor-id', str(command_admin.id),
        )
    assert not snapshot_path.exists()

    _write_plan(plan_path, plan)
    OperationGrant.objects.create(user=user, code='view_reports')
    with pytest.raises(CommandError, match='发生变化'):
        call_command(
            'migrate_granular_permissions', '--apply', '--plan', str(plan_path),
            '--confirm', plan['plan_id'], '--snapshot', str(snapshot_path),
            '--actor-id', str(command_admin.id),
        )
    assert not snapshot_path.exists()


@pytest.mark.django_db
def test_restore_refuses_to_overwrite_permissions_changed_after_apply(branch, tmp_path, command_admin):
    user = _user('13910000007', '恢复保护用户', branch=branch)
    OperationGrant.objects.create(user=user, code='approve_inventory')
    OperationGrant.objects.create(user=user, code='view_inventory')
    plan = build_migration_plan()
    plan_path = tmp_path / 'plan.json'
    snapshot_path = tmp_path / 'snapshot.json'
    _write_plan(plan_path, plan)
    call_command(
        'migrate_granular_permissions', '--apply', '--plan', str(plan_path),
        '--confirm', plan['plan_id'], '--snapshot', str(snapshot_path),
        '--actor-id', str(command_admin.id), '--accept-unmapped',
    )

    OperationGrant.objects.create(user=user, code='view_reports')
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    with pytest.raises(CommandError, match='拒绝覆盖'):
        call_command(
            'migrate_granular_permissions', '--restore-snapshot', str(snapshot_path),
            '--confirm-restore', snapshot['snapshot_id'], '--actor-id', str(command_admin.id),
        )
    assert OperationGrant.objects.filter(user=user, code='review_inventory').exists()
    assert OperationGrant.objects.filter(user=user, code='view_reports').exists()


@pytest.mark.django_db
def test_snapshot_checksum_detects_corruption(branch, tmp_path, command_admin):
    user = _user('13910000008', '快照用户', branch=branch)
    OperationGrant.objects.create(user=user, code='approve_inventory')
    OperationGrant.objects.create(user=user, code='view_inventory')
    plan = build_migration_plan()
    plan_path = tmp_path / 'plan.json'
    snapshot_path = tmp_path / 'snapshot.json'
    _write_plan(plan_path, plan)
    call_command(
        'migrate_granular_permissions', '--apply', '--plan', str(plan_path),
        '--confirm', plan['plan_id'], '--snapshot', str(snapshot_path),
        '--actor-id', str(command_admin.id), '--accept-unmapped',
    )

    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    snapshot['authorization']['grants'].clear()
    snapshot_path.write_text(json.dumps(snapshot), encoding='utf-8')
    with pytest.raises(CommandError, match='摘要校验失败'):
        call_command('migrate_granular_permissions', '--verify-snapshot', str(snapshot_path))
