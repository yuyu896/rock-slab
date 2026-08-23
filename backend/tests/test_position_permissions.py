"""岗位模板 + 任命即授权 + 权限可见性（小案③ 权限重构）测试。"""
import pytest
from conftest import _client_for
from rest_framework import status

from apps.permissions.models import ManagementScope, OperationGrant
from apps.permissions.positions import POSITION_TEMPLATES


# ---------------------------------------------------------------------------
# 任命即授权（resolve_user_scope）
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAppointmentScope:
    def _fresh(self, db, branch, team, region):
        from apps.users.models import User
        return User.objects.create_user(
            phone='13500000001', name='受任者', password='x',
            role='staff', status='active',
        )

    def test_region_manager_gets_region_subtree(self, region, team, branch):
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13500000001', name='区长', password='x', role='staff', status='active',
        )
        region.manager = user
        region.save(update_fields=['manager'])
        scope = resolve_user_scope(user)
        assert branch.id in scope.branches
        assert region.id in scope.appointed_regions

    def test_team_leader_gets_team_branches(self, team, branch):
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13500000002', name='组长', password='x', role='staff', status='active',
        )
        team.leader = user
        team.save(update_fields=['leader'])
        scope = resolve_user_scope(user)
        assert branch.id in scope.branches

    def test_branch_manager_scope(self, branch):
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13500000003', name='分公司负责人', password='x', role='staff', status='active',
        )
        branch.manager = user
        branch.save(update_fields=['manager'])
        scope = resolve_user_scope(user)
        assert branch.id in scope.branches

    def test_appointment_unions_with_grant(self, region, second_region, second_branch, branch):
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13500000004', name='兼任者', password='x', role='staff', status='active',
        )
        region.manager = user
        region.save(update_fields=['manager'])
        ManagementScope.objects.create(user=user, branch=second_branch)
        scope = resolve_user_scope(user)
        assert branch.id in scope.branches and second_branch.id in scope.branches

    def test_appointment_removed_scope_revoked(self, region, branch):
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13500000005', name='卸任者', password='x', role='staff', status='active',
        )
        region.manager = user
        region.save(update_fields=['manager'])
        assert branch.id in resolve_user_scope(user).branches

        region.manager = None
        region.save(update_fields=['manager'])
        fresh = User.objects.get(pk=user.pk)  # 绕过单请求缓存
        assert branch.id not in resolve_user_scope(fresh).branches

    def test_is_empty_considers_appointments(self, region, branch):
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13500000006', name='仅任命', password='x', role='staff', status='active',
        )
        assert resolve_user_scope(user).is_empty is True
        region.manager = user
        region.save(update_fields=['manager'])
        fresh = User.objects.get(pk=user.pk)
        assert resolve_user_scope(fresh).is_empty is False


# ---------------------------------------------------------------------------
# 岗位目录接口 / supervisor 退役
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPositionTemplatesApi:
    def test_catalog_contains_five_positions(self, authenticated_client):
        resp = authenticated_client.get('/api/permissions/position-templates')
        assert resp.status_code == status.HTTP_200_OK
        roles = {t['role'] for t in resp.data}
        assert roles == {'admin', 'director', 'manager', 'leader', 'staff'}
        by_role = {t['role']: t for t in resp.data}
        assert 'approve_transfer' in by_role['manager']['operations']
        assert by_role['leader']['operations'] == []
        assert by_role['admin']['all_operations'] is True

    def test_create_user_supervisor_rejected(self, authenticated_client):
        resp = authenticated_client.post('/api/users/', {
            'phone': '13611112222', 'name': '退役岗位', 'role': 'supervisor',
            'status': 'active', 'password': 'x123456',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_legacy_supervisor_user_still_works(self, db, branch):
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13622223333', name='存量主管', password='x',
            role='supervisor', status='active', branch=branch,
        )
        OperationGrant.objects.create(user=user, code='approve_transfer')
        assert user.can('approve_transfer') is True


# ---------------------------------------------------------------------------
# 生效权限总览 / me 扩展
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEffectiveApi:
    def test_non_admin_forbidden(self, staff_client):
        resp = staff_client.get('/api/permissions/effective')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_gets_all_users_with_appointments(
        self, authenticated_client, region, branch, staff_user,
    ):
        region.manager = staff_user
        region.save(update_fields=['manager'])
        resp = authenticated_client.get('/api/permissions/effective')
        assert resp.status_code == status.HTTP_200_OK
        row = next(r for r in resp.data if r['user'] == str(staff_user.id))
        assert {'type': 'region', 'id': str(region.id), 'name': region.name} in row['appointments']
        assert row['scope_summary']['branch_count'] >= 1

    def test_admin_row_has_all_operations(self, authenticated_client, admin_user):
        resp = authenticated_client.get('/api/permissions/effective')
        row = next(r for r in resp.data if r['user'] == str(admin_user.id))
        assert row['operations'] is None and row['scope_summary']['all'] is True

    def test_me_includes_appointments_and_summary(self, region, branch, staff_user):
        region.manager = staff_user
        region.save(update_fields=['manager'])
        client = _client_for(staff_user)
        resp = client.get('/api/permissions/me')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['appointments'][0]['type'] == 'region'
        assert resp.data['scope_summary']['branch_count'] >= 1


# ---------------------------------------------------------------------------
# 通知路由按操作授权
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNotificationRoutingByGrant:
    def _make_pending_transfer(self, branch_name):
        from apps.transfers.models import Transfer
        import datetime
        return Transfer.objects.create(
            action_type='transfer', 资产编号='NP-001', 资产名称='测试资产',
            调拨数量=1, 调出分公司=branch_name, 审批状态='待审批',
            调拨日期=datetime.date.today(),
        )

    def test_grant_holder_receives_approval_notification(self, db, branch, staff_user):
        from apps.notifications.models import Notification
        OperationGrant.objects.create(user=staff_user, code='approve_transfer')
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
# migrate_positions：逐人 diff，只补不删
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
        assert 'supervisor→manager' in out

    def test_apply_changes_role_and_grants_without_deleting(self, db, branch):
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13655556666', name='执行换岗', password='x',
            role='supervisor', status='active', branch=branch,
        )
        # 既有额外授权（模板外）+ 部分模板授权
        OperationGrant.objects.create(user=user, code='view_audit')
        OperationGrant.objects.create(user=user, code='approve_transfer')

        self._run('--apply')

        user.refresh_from_db()
        assert user.role == 'manager'
        codes = set(OperationGrant.objects.filter(user=user).values_list('code', flat=True))
        template = set(POSITION_TEMPLATES['manager']['operations'])
        assert template.issubset(codes)  # 模板补齐
        assert 'view_audit' in codes      # 额外授权保留（只补不删）

    def test_apply_idempotent(self, db, branch):
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13666667777', name='幂等', password='x',
            role='manager', status='active', branch=branch,
        )
        self._run('--apply')
        count_after_first = OperationGrant.objects.filter(user=user).count()
        self._run('--apply')
        assert OperationGrant.objects.filter(user=user).count() == count_after_first
        assert '无变化 1 人' in self._run()
