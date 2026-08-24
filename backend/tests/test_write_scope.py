"""
写操作数据范围校验回归测试（write-authorization-scoping）。

验证：即便业务发起（流转/盘点创建）按产品设计对所有登录用户开放，操作者也只能
作用于其授权范围内的分公司——跨范围写操作必须被拒；盘点 check 提交跨范围资产必须 404。
"""
import pytest
from conftest import _client_for


@pytest.mark.django_db
class TestWriteScopeEnforcement:
    def test_transfer_create_out_of_scope_rejected(self, staff_user, second_branch, item_id):
        # staff_user 授权范围 = fixture branch，对第二分公司发起调拨应被拒
        client = _client_for(staff_user)
        resp = client.post('/api/transfers/transfer', {
            '调拨日期': '2026-01-15',
            '调出分公司': second_branch.name,
            '调入分公司': second_branch.name,
            'items': [{'item': item_id('SCOPE-OUT-001'), '数量': 1}],
        }, format='json')
        assert resp.status_code == 400

    def test_transfer_create_in_scope_allowed(self, staff_user, branch, item_id):
        # staff_user 对自己授权分公司发起调拨应通过 scope 校验
        client = _client_for(staff_user)
        resp = client.post('/api/transfers/transfer', {
            '调拨日期': '2026-01-15',
            '调出分公司': branch.name,
            '调入分公司': branch.name,
            'items': [{'item': item_id('SCOPE-IN-001'), '数量': 1}],
        }, format='json')
        assert resp.status_code == 201

    def test_inventory_create_out_of_scope_rejected(self, staff_user, second_branch):
        client = _client_for(staff_user)
        resp = client.post('/api/inventories/', {
            'name': '越权盘点',
            'branch': second_branch.id,
        }, format='json')
        assert resp.status_code == 400

    def test_check_asset_out_of_branch_rejected(
        self, staff_user, admin_user, branch, second_branch,
    ):
        """盘点 check 提交不属于任务分公司的资产 → 404（IDOR 修复）。"""
        from apps.assets.models import AssetStock
        from apps.assets.services import ledger
        from apps.categories.models import Category
        item, _ = Category.objects.get_or_create(
            asset_code='CROSS-CHECK-001',
            defaults={'asset_category': '固定', 'item_category': '办公',
                      'asset_name': '跨范围资产', 'unit': '件'},
        )
        ledger.apply_adjustment(second_branch, item, ledger.COLUMN_STOCK, 5, '造数')
        stock = AssetStock.objects.get(branch=second_branch, item=item)
        client_admin = _client_for(admin_user)
        resp = client_admin.post('/api/inventories/', {'name': '跨范围盘点', 'branch': branch.id})
        assert resp.status_code == 201
        task_id = resp.data['id']
        assert client_admin.post(f'/api/inventories/{task_id}/start').status_code == 200

        client_staff = _client_for(staff_user)
        resp = client_staff.post(f'/api/inventories/{task_id}/check', {
            'stockId': str(stock.id), 'qty': 1,
        }, format='json')
        assert resp.status_code == 404


@pytest.mark.django_db
class TestWritePermissionBaseline:
    """关键写 action 权限声明基线（防回归）。

    业务发起 action（purchase/assign/return/transfer/recovery）按产品设计对所有登录
    用户开放，不在本约束内；审批 / 入库 / 导入类必须声明权限码。
    """

    def test_transfer_sensitive_actions_declared(self):
        from apps.transfers.views import TransferViewSet
        required = TransferViewSet.required_operations
        for action in ('import_excel', 'approve', 'warehouse'):
            assert action in required, f'transfers.{action} 必须在 required_operations 中声明'

    def test_assets_write_endpoints_frozen(self):
        """P1 起 Asset 写接口整体下线（405），无需再声明编辑操作码。"""
        from importlib import import_module
        views = import_module('apps.assets.views')
        assert not hasattr(views, 'AssetViewSet')

@pytest.mark.django_db
class TestUserDirectoryScoping:
    """用户列表 / 详情按数据范围隔离（write-authorization-scoping R4）。"""

    def test_non_admin_list_users_excludes_out_of_scope(self, staff_user, staff_b):
        # staff_user 仅见授权范围内 + 本人，看不到另一区域的 staff_b
        client = _client_for(staff_user)
        resp = client.get('/api/users/')
        assert resp.status_code == 200
        ids = {str(u['id']) for u in resp.data}
        assert str(staff_user.id) in ids
        assert str(staff_b.id) not in ids

    def test_non_admin_retrieve_out_of_scope_user_404(self, staff_user, staff_b):
        client = _client_for(staff_user)
        resp = client.get(f'/api/users/{staff_b.id}')
        assert resp.status_code == 404
