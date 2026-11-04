"""管理授权模型测试：解耦后权限由 ManagementScope / OperationGrant 决定，而非 role。

覆盖 spec 关键场景：
  - 正向状态：授予单个组织节点 → 范围收窄
  - 跨组织授权叠加 → 范围并集
  - 接口权限按业务操作授权判断（非角色等级）
  - admin 全权且不走授权
  - 无授权非 admin → 空范围
"""
import pytest
from rest_framework import status
from apps.permissions.models import ManagementScope, OperationGrant
from conftest import _client_for


@pytest.mark.django_db
class TestScopeResolution:
    def test_admin_resolves_to_all(self, admin_user):
        from apps.permissions.scope import resolve_user_scope
        assert resolve_user_scope(admin_user).all is True

    def test_account_without_override_uses_only_its_assigned_branch(self, branch, second_branch):
        """岗位不扩展数据范围；未单独设置时沿用账号分公司归属。"""
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13600000001', name='无授权主管', password='test123456',
            role='supervisor', branch=branch,
        )
        scope = resolve_user_scope(user)
        assert scope.all is False
        assert scope.branches == {branch.id}
        assert second_branch.id not in scope.branches

    def test_grant_single_branch_narrows_scope(self, branch, second_branch):
        """授予单个分公司 → 仅见该分公司数据。"""
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13600000002', name='仅一分公司', password='test123456', role='staff',
        )
        ManagementScope.objects.create(user=user, branch=branch)
        scope = resolve_user_scope(user)
        assert scope.branches == {branch.id}
        assert second_branch.id not in scope.branches

    def test_region_grant_expands_to_branches(self, region, branch):
        """授予大区 → 展开为旗下全部分公司。"""
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13600000003', name='大区授权', password='test123456', role='staff',
        )
        ManagementScope.objects.create(user=user, region=region)
        scope = resolve_user_scope(user)
        assert region.id in scope.regions
        assert branch.id in scope.branches  # region 展开包含旗下分公司

    def test_multiple_grants_union(self, branch, second_branch):
        """跨组织授权叠加 → 范围并集。"""
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13600000004', name='多节点', password='test123456', role='staff',
        )
        ManagementScope.objects.create(user=user, branch=branch)
        ManagementScope.objects.create(user=user, branch=second_branch)
        scope = resolve_user_scope(user)
        assert scope.branches == {branch.id, second_branch.id}


@pytest.mark.django_db
class TestDataScopeByGrant:
    def test_staff_granted_branch_sees_only_that_branch(
        self, branch, second_branch, make_stock, make_stock_b,
    ):
        """被授予某分公司的 staff 仅见该分公司台账行（数据范围由授权决定）。"""
        from apps.users.models import User
        make_stock()  # branch
        make_stock_b()  # second_branch
        user = User.objects.create_user(
            phone='13600000010', name='范围用户', password='test123456', role='staff',
        )
        ManagementScope.objects.create(user=user, branch=branch)
        OperationGrant.objects.create(user=user, code='view_asset_ledger')
        client = _client_for(user)
        resp = client.get('/api/assets/summary')
        assert resp.status_code == 200
        assert resp.data['count'] == 1
        assert resp.data['results'][0]['branch_name'] == branch.name

    def test_staff_without_grant_sees_nothing(self, make_stock):
        """无授权的非 admin 用户见空范围。"""
        from apps.users.models import User
        make_stock()
        user = User.objects.create_user(
            phone='13600000011', name='无范围', password='test123456', role='staff',
        )
        OperationGrant.objects.create(user=user, code='view_asset_ledger')
        client = _client_for(user)
        resp = client.get('/api/assets/summary')
        assert resp.status_code == 200
        assert resp.data['count'] == 0


@pytest.mark.django_db
class TestOperationPermission:
    def test_operation_grant_is_independent_of_scope_and_other_operations(self, branch):
        """业务操作授权按单项生效，不由数据范围或岗位推导。"""
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13600000020', name='授权专员', password='test123456', role='staff',
        )
        ManagementScope.objects.create(user=user, branch=branch)
        OperationGrant.objects.create(user=user, code='view_asset_ledger')
        assert user.can('view_asset_ledger') is True
        assert user.can('adjust_asset_ledger') is False
        assert resolve_user_scope(user).branches == {branch.id}

    def test_admin_can_anything_without_grant(self, admin_user):
        """admin 恒真，不查授权。"""
        assert admin_user.can('manage_assets') is True
        assert admin_user.can('any_code_not_in_registry') is True

    def test_no_grant_no_operation(self, branch):
        """普通账号即使有岗位和分公司归属，也不会自动得到业务权限。"""
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13600000021', name='未授权', password='test123456',
            role='manager', branch=branch,
        )
        assert user.can('view_asset_ledger') is False
        assert user.can('create_purchase') is False
        assert resolve_user_scope(user).branches == {branch.id}


@pytest.mark.django_db
class TestManagementScopeModel:
    def test_exactly_one_org_node_enforced(self, region, branch):
        """ManagementScope 必须至多一个组织节点。"""
        from django.core.exceptions import ValidationError
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13600000030', name='约束测试', password='test123456', role='staff',
        )
        # 无节点 → clean 校验失败
        scope = ManagementScope(user=user)
        with pytest.raises(ValidationError):
            scope.clean()
        # 多节点 → clean 校验失败
        scope_multi = ManagementScope(user=user, region=region, branch=branch)
        with pytest.raises(ValidationError):
            scope_multi.clean()

    def test_duplicate_grant_prevented(self, region):
        """同一员工对同一节点不能重复授权。"""
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13600000031', name='去重测试', password='test123456', role='staff',
        )
        ManagementScope.objects.create(user=user, region=region)
        with pytest.raises(Exception):
            ManagementScope.objects.create(user=user, region=region)


@pytest.mark.django_db
class TestAllDataScope:
    def test_is_all_data_resolves_to_all(self, branch):
        """is_all_data 授权 → 数据范围全部。"""
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13600000040', name='全局授权', password='test123456', role='staff',
        )
        ManagementScope.objects.create(user=user, is_all_data=True)
        assert resolve_user_scope(user).all is True

    def test_is_all_data_covers_future_branches(self, branch, second_branch):
        """is_all_data 授权后，新增分公司也自动覆盖。"""
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13600000041', name='未来覆盖', password='test123456', role='staff',
        )
        ManagementScope.objects.create(user=user, is_all_data=True)
        # second_branch 是后创建/已存在的另一分公司，应被全部覆盖（无需逐个授权）
        scope = resolve_user_scope(user)
        assert scope.all is True

    def test_duplicate_is_all_data_prevented(self):
        """同一用户不能有两条 is_all_data 授权。"""
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13600000042', name='重复全局', password='test123456', role='staff',
        )
        ManagementScope.objects.create(user=user, is_all_data=True)
        with pytest.raises(Exception):
            ManagementScope.objects.create(user=user, is_all_data=True)

    def test_is_all_data_with_node_rejected_by_clean(self, region):
        """is_all_data 与具体节点互斥（模型 clean 校验）。"""
        from django.core.exceptions import ValidationError
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13600000043', name='互斥测试', password='test123456', role='staff',
        )
        scope = ManagementScope(user=user, is_all_data=True, region=region)
        with pytest.raises(ValidationError):
            scope.clean()


@pytest.mark.django_db
class TestAllDataApi:
    def test_authorization_api_replaces_scope_without_granting_operations(self, admin_user, branch):
        """完整授权配置可单独更新数据范围，且不隐式授予业务操作。"""
        from apps.users.models import User
        from apps.permissions.scope import resolve_user_scope
        user = User.objects.create_user(
            phone='13600000050', name='全量范围API', password='test123456', role='staff',
        )
        client = _client_for(admin_user)
        url = f'/api/permissions/users/{user.id}/authorization'
        response = client.put(url, {
            'operations': [],
            'scope': {'mode': 'all', 'nodes': []},
        }, format='json')
        assert response.status_code == 200
        assert response.data['scope']['mode'] == 'all'
        assert response.data['operations'] == []
        user.refresh_from_db()
        assert resolve_user_scope(user).all is True
        assert user.can('view_asset_ledger') is False

    def test_all_scope_with_nodes_returns_400(self, admin_user, region):
        """全部数据范围不能同时包含具体组织节点。"""
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13600000051', name='互斥API', password='test123456', role='staff',
        )
        client = _client_for(admin_user)
        r = client.put(f'/api/permissions/users/{user.id}/authorization', {
            'operations': [],
            'scope': {
                'mode': 'all',
                'nodes': [{'type': 'region', 'id': str(region.id)}],
            },
        }, format='json')
        assert r.status_code == 400

    def test_duplicate_scope_node_returns_400(self, admin_user, region):
        """一个授权配置不能重复提交同一组织节点。"""
        from apps.users.models import User
        user = User.objects.create_user(
            phone='13600000052', name='重复节点API', password='test123456', role='staff',
        )
        client = _client_for(admin_user)
        r = client.put(f'/api/permissions/users/{user.id}/authorization', {
            'operations': [],
            'scope': {
                'mode': 'custom',
                'nodes': [
                    {'type': 'region', 'id': str(region.id)},
                    {'type': 'region', 'id': str(region.id)},
                ],
            },
        }, format='json')
        assert r.status_code == 400
