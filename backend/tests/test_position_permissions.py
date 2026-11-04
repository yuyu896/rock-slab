"""Account-level permissions and data-scope regression tests."""
import pytest
from conftest import _client_for
from rest_framework import status

from apps.permissions.models import ManagementScope, OperationGrant


# ---------------------------------------------------------------------------
# Position appointments do not grant data scope.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAccountScope:
    def test_region_appointment_does_not_expand_default_branch_scope(
        self, region, branch, second_branch,
    ):
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13500000001', name='区长', password='x', role='manager',
            status='active', branch=branch,
        )
        region.manager = user
        region.save(update_fields=['manager'])
        scope = resolve_user_scope(user)
        assert scope.branches == {branch.id}
        assert second_branch.id not in scope.branches

    def test_team_appointment_does_not_create_scope_without_branch(self, team, branch):
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13500000002', name='组长', password='x', role='leader', status='active',
        )
        team.leader = user
        team.save(update_fields=['leader'])
        scope = resolve_user_scope(user)
        assert scope.is_empty

    def test_branch_appointment_does_not_create_scope_without_branch(self, branch):
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13500000003', name='分公司负责人', password='x', role='staff', status='active',
        )
        branch.manager = user
        branch.save(update_fields=['manager'])
        assert resolve_user_scope(user).is_empty

    def test_explicit_scope_is_independent_of_appointment(
        self, region, second_branch, branch,
    ):
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13500000004', name='兼任者', password='x', role='staff', status='active',
        )
        region.manager = user
        region.save(update_fields=['manager'])
        ManagementScope.objects.create(user=user, branch=second_branch)
        scope = resolve_user_scope(user)
        assert scope.branches == {second_branch.id}
        assert branch.id not in scope.branches

    def test_default_branch_scope_does_not_depend_on_appointment(self, region, branch):
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13500000005', name='默认归属', password='x', role='staff',
            status='active', branch=branch,
        )
        region.manager = user
        region.save(update_fields=['manager'])
        assert resolve_user_scope(user).branches == {branch.id}

        region.manager = None
        region.save(update_fields=['manager'])
        fresh = User.objects.get(pk=user.pk)  # 绕过单请求缓存
        assert resolve_user_scope(fresh).branches == {branch.id}

    def test_scope_without_branch_or_explicit_nodes_is_empty(self, region, branch):
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13500000006', name='仅任命', password='x', role='staff', status='active',
        )
        assert resolve_user_scope(user).is_empty is True
        region.manager = user
        region.save(update_fields=['manager'])
        fresh = User.objects.get(pk=user.pk)
        assert resolve_user_scope(fresh).is_empty is True

    def test_is_empty_treats_all_data_as_non_empty(self, db):
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13500000007', name='全数据', password='x', role='manager', status='active',
        )
        ManagementScope.objects.create(user=user, is_all_data=True)
        scope = resolve_user_scope(User.objects.get(pk=user.pk))
        assert scope.all is True
        assert scope.is_empty is False  # 全部数据授权 = 最广范围，不得误报为空


# ---------------------------------------------------------------------------
# 岗位目录接口 / supervisor 退役
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPositionTemplatesApi:
    def test_position_template_catalog_exposes_confirmed_baselines(self, authenticated_client):
        resp = authenticated_client.get('/api/permissions/position-templates')
        assert resp.status_code == status.HTTP_200_OK
        assert {row['role'] for row in resp.data} == {'manager', 'leader', 'director'}
        assert all(row['version'] for row in resp.data)

    def test_create_user_supervisor_rejected(self, authenticated_client):
        resp = authenticated_client.post('/api/users/', {
            'phone': '13611112222', 'name': '退役岗位', 'role': 'supervisor',
            'status': 'active', 'password': 'x123456',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_user_staff_rejected(self, authenticated_client):
        resp = authenticated_client.post('/api/users/', {
            'phone': '13611112223', 'name': '退役行政', 'role': 'staff',
            'status': 'active', 'password': 'x123456',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_legacy_supervisor_user_is_read_only_history(self, db, branch):
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13622223333', name='存量主管', password='x',
            role='supervisor', status='active', branch=branch,
        )
        OperationGrant.objects.create(user=user, code='approve_transfer')
        assert user.can('approve_transfer') is False

    def test_legacy_staff_user_is_read_only_history(self, db, branch):
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13622223334', name='存量行政', password='x',
            role='staff', status='active', branch=branch,
        )
        ManagementScope.objects.create(user=user, branch=branch)
        OperationGrant.objects.create(user=user, code='manage_assets')
        from apps.permissions.scope import resolve_user_scope
        assert user.can('manage_assets') is False
        assert branch.id in resolve_user_scope(user).branches


# ---------------------------------------------------------------------------
# 生效权限总览 / me 扩展
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEffectiveApi:
    def test_non_admin_forbidden(self, staff_client):
        resp = staff_client.get('/api/permissions/effective')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_gets_actual_user_scope_without_appointments(
        self, authenticated_client, region, branch, staff_user,
    ):
        region.manager = staff_user
        region.save(update_fields=['manager'])
        resp = authenticated_client.get('/api/permissions/effective')
        assert resp.status_code == status.HTTP_200_OK
        row = next(r for r in resp.data if r['user'] == str(staff_user.id))
        assert 'appointments' not in row
        assert row['scope']['mode'] == 'default'
        assert row['scope_summary']['branch_count'] == 1

    def test_admin_row_has_all_operations(self, authenticated_client, admin_user):
        resp = authenticated_client.get('/api/permissions/effective')
        row = next(r for r in resp.data if r['user'] == str(admin_user.id))
        assert row['operations'] is None and row['scope_summary']['all'] is True

    def test_me_includes_account_scope_summary_without_appointments(self, region, branch, staff_user):
        region.manager = staff_user
        region.save(update_fields=['manager'])
        client = _client_for(staff_user)
        resp = client.get('/api/permissions/me')
        assert resp.status_code == status.HTTP_200_OK
        assert 'appointments' not in resp.data
        assert resp.data['scope']['mode'] == 'default'
        assert resp.data['scope_summary']['branch_count'] == 1


# ---------------------------------------------------------------------------
# 通知路由按操作授权
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNotificationRoutingByGrant:
    def _make_pending_transfer(self, branch_name):
        from apps.transfers.models import Transfer, TransferLine
        from apps.categories.models import Category
        from apps.notifications.signals import notify_transfer_created
        import datetime
        item, _ = Category.objects.get_or_create(
            asset_code='NP-001',
            defaults={
                'asset_category': '测试类目', 'item_category': '测试分类',
                'asset_name': '通知测试资产', 'unit': '个',
            },
        )
        t = Transfer.objects.create(
            action_type='transfer', 调出分公司=branch_name, 审批状态='待审批',
            调拨日期=datetime.date.today(),
        )
        TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=1)
        # 明细行齐备后显式触发创建通知（与视图 _notify_created 同口径；
        # 单头 post_save 触发时行尚未建，信号侧会静默跳过）
        notify_transfer_created(t)
        return t

    def test_grant_holder_receives_approval_notification(self, db, branch, staff_user):
        from apps.notifications.models import Notification
        staff_user.role = 'leader'
        staff_user.save(update_fields=['role'])
        OperationGrant.objects.create(user=staff_user, code='approve_internal_transfer')
        OperationGrant.objects.create(user=staff_user, code='view_transfer')
        self._make_pending_transfer(branch.name)
        assert Notification.objects.filter(
            recipient=staff_user, notification_type='approval',
        ).exists()

    def test_high_position_without_grant_not_notified(self, db, branch):
        from apps.users.models import User
        from apps.notifications.models import Notification
        director = User.objects.create_user(
            phone='13633334444', name='无授权总监', password='x',
            role='director', status='active',
        )
        self._make_pending_transfer(branch.name)
        assert not Notification.objects.filter(recipient=director).exists()

    def test_admin_still_notified(self, db, branch, admin_user):
        from apps.notifications.models import Notification
        self._make_pending_transfer(branch.name)
        assert Notification.objects.filter(
            recipient=admin_user, notification_type='approval',
        ).exists()


# ---------------------------------------------------------------------------
# migrate_positions：仅调整退役岗位标记
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMigratePositionsCommand:
    def _run(self, *args):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('migrate_positions', *args, stdout=out)
        return out.getvalue()

    def test_dry_run_does_not_write(self, db, branch):
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13644445555', name='待换岗主管', password='x',
            role='supervisor', status='active', branch=branch,
        )
        out = self._run()
        user.refresh_from_db()
        assert user.role == 'supervisor'  # dry-run 不写库
        assert 'supervisor' in out and 'manager' in out

    def test_apply_changes_role_clears_grants_and_scope_with_audit(self, db, branch, admin_user):
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13655556666', name='执行换岗', password='x',
            role='supervisor', status='active', branch=branch,
        )
        OperationGrant.objects.create(user=user, code='approve_transfer')
        ManagementScope.objects.create(user=user, branch=branch)

        out = self._run('--apply', '--actor-id', str(admin_user.id))

        user.refresh_from_db()
        assert user.role == 'manager'
        assert not OperationGrant.objects.filter(user=user).exists()
        assert not ManagementScope.objects.filter(user=user).exists()
        assert '清理原授权并记录审计' in out
        from apps.audit.models import AuditLog
        log = AuditLog.objects.get(resource_type='user_authorization', resource_id=user.id)
        assert log.user_id == admin_user.id
        assert log.before_data['operations'] == ['approve_transfer']
        assert log.after_data == {'role': 'manager', 'operations': [], 'scopes': []}

    def test_apply_idempotent(self, db, branch, admin_user):
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13666667777', name='幂等', password='x',
            role='manager', status='active', branch=branch,
        )
        self._run('--apply', '--actor-id', str(admin_user.id))
        count_after_first = OperationGrant.objects.filter(user=user).count()
        self._run('--apply', '--actor-id', str(admin_user.id))
        assert OperationGrant.objects.filter(user=user).count() == count_after_first
        assert '更新退役岗位标记 0 人' in self._run()

    def test_apply_migrates_staff_marker_and_clears_old_authorization(self, db, branch, admin_user):
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13677778888', name='存量行政', password='x',
            role='staff', status='active', branch=branch,
        )
        ManagementScope.objects.create(user=user, branch=branch)
        OperationGrant.objects.create(user=user, code='approve_inventory')  # 模板外特例

        self._run('--apply', '--actor-id', str(admin_user.id))

        user.refresh_from_db()
        assert user.role == 'manager'
        assert not OperationGrant.objects.filter(user=user).exists()
        assert not ManagementScope.objects.filter(user=user).exists()


# ---------------------------------------------------------------------------
# seed_position_grants：退役命令必须只读
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSeedPositionGrantsCommand:
    def _run(self, *args):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('seed_position_grants', *args, stdout=out)
        return out.getvalue()

    def test_dry_run_does_not_write(self, db, branch):
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13611112222', name='预演行政', password='x',
            role='manager', status='active', branch=branch,
        )
        out = self._run()
        assert not OperationGrant.objects.filter(user=user).exists()
        assert not ManagementScope.objects.filter(user=user).exists()
        assert '已停用' in out

    def test_apply_refuses_and_preserves_all_existing_records(self, db, branch, admin_user):
        from django.core.management.base import CommandError
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13611112233', name='在职行政', password='x',
            role='manager', status='active', branch=branch,
        )
        OperationGrant.objects.create(user=user, code='approve_transfer')
        ManagementScope.objects.create(user=user, branch=branch)
        ManagementScope.objects.create(user=admin_user, branch=branch)
        OperationGrant.objects.create(user=admin_user, code='manage_users')
        before_grants = set(OperationGrant.objects.values_list('pk', 'user_id', 'code'))
        before_scopes = set(ManagementScope.objects.values_list('pk', 'user_id', 'branch_id'))

        with pytest.raises(CommandError, match='已停用'):
            self._run('--apply')

        assert set(OperationGrant.objects.values_list('pk', 'user_id', 'code')) == before_grants
        assert set(ManagementScope.objects.values_list('pk', 'user_id', 'branch_id')) == before_scopes

    def test_check_seed_grants_accepts_new_account_without_explicit_grants(self, db, branch):
        from io import StringIO
        from django.core.management import call_command
        from apps.users.models import User
        User.objects.create_user(
            phone='13611112288', name='尚未授权的新账号', password='x',
            role='manager', status='active', branch=branch,
        )
        out = StringIO()
        call_command('check_seed_grants', stdout=out)
        assert '授权为空是允许状态' in out.getvalue()
