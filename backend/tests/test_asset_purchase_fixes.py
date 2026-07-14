"""资产编辑(PATCH) / 采购草稿 / 采购审批入库联动 修复测试。"""
import pytest
from conftest import _client_for


def _action_url(action, pk=None):
    return f'/api/transfers/{pk}/{action}' if pk else f'/api/transfers/{action}'


@pytest.mark.django_db
class TestAssetEditPatch:
    def test_patch_status_succeeds(self, admin_user, branch):
        from apps.assets.models import Asset
        asset = Asset.objects.create(
            序号=1, 分公司=branch.name, 分公司编号=branch.code, branch=branch,
            资产编号='EDT-001', 资产类目='固定', 物品分类='办公',
            资产名称='编辑测试', 数量=1, 当前状态='在库',
        )
        client = _client_for(admin_user)
        # 仅改状态（不传资产编号等必填字段），PATCH 应成功（修复前 PUT 会报错）
        resp = client.patch(f'/api/assets/{asset.id}', {'当前状态': '使用中'}, format='json')
        assert resp.status_code == 200
        asset.refresh_from_db()
        assert asset.当前状态 == '使用中'


@pytest.mark.django_db
class TestPurchaseApproveStock:
    def _create_purchase(self, client, branch, code):
        resp = client.post(_action_url('purchase'), {
            '调拨日期': '2026-07-14', '资产编号': code, '资产名称': '采购物',
            '调拨数量': 5, '调拨原因': '采购', '调出分公司': branch.name,
        }, format='json')
        assert resp.status_code == 201
        return resp.data['id']

    def test_approve_creates_asset(self, admin_user, branch):
        from apps.assets.models import Asset
        client = _client_for(admin_user)
        tid = self._create_purchase(client, branch, 'APR-001')
        resp = client.post(f'/api/transfers/{tid}/approve', {'approved': True}, format='json')
        assert resp.status_code == 200
        assert resp.data['审批状态'] == '已入库'
        a = Asset.objects.get(资产编号='APR-001')
        assert a.数量 == 5
        assert a.分公司 == branch.name

    def test_approve_increments_existing(self, admin_user, branch):
        from apps.assets.models import Asset
        Asset.objects.create(
            序号=1, 分公司=branch.name, 分公司编号=branch.code, branch=branch,
            资产编号='APR-002', 资产类目='固定', 物品分类='办公',
            资产名称='已有', 数量=3, 当前状态='在库',
        )
        client = _client_for(admin_user)
        tid = self._create_purchase(client, branch, 'APR-002')
        resp = client.post(f'/api/transfers/{tid}/approve', {'approved': True}, format='json')
        assert resp.status_code == 200
        a = Asset.objects.get(资产编号='APR-002')
        assert a.数量 == 8  # 3 + 5


@pytest.mark.django_db
class TestPurchaseDraft:
    def test_create_draft(self, admin_user):
        from apps.transfers.models import Transfer
        client = _client_for(admin_user)
        resp = client.post(_action_url('purchase'), {
            '调拨日期': '2026-07-14', '资产编号': 'DRF-001', '资产名称': '草稿物',
            '调拨数量': 1, '调出分公司': '测试分公司', 'draft': True,
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['审批状态'] == '草稿'
        assert Transfer.objects.get(资产编号='DRF-001').审批状态 == '草稿'

    def test_submit_draft(self, admin_user):
        client = _client_for(admin_user)
        resp = client.post(_action_url('purchase'), {
            '调拨日期': '2026-07-14', '资产编号': 'DRF-002', '资产名称': '草稿物',
            '调拨数量': 1, '调出分公司': '测试分公司', 'draft': True,
        }, format='json')
        tid = resp.data['id']
        resp2 = client.post(f'/api/transfers/{tid}/submit', format='json')
        assert resp2.status_code == 200
        assert resp2.data['审批状态'] == '待审批'
