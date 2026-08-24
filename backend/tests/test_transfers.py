"""
Tests for Transfer flow: purchase, assign, return, transfer, approve, asset sync.
"""
import pytest
from rest_framework import status

TRANSFER_LIST_URL = '/api/transfers/'


def _action_url(action_name, pk=None):
    if pk:
        return f'/api/transfers/{pk}/{action_name}'
    return f'/api/transfers/{action_name}'


@pytest.fixture
def purchase_payload(item_id):
    return {
        '调拨日期': '2026-01-15',
        '调拨原因': '采购入库测试',
        '调出分公司': '测试分公司',
        'items': [{'item': item_id('AST-TEST-001'), '数量': 1}],
    }


@pytest.fixture
def assign_payload(item_id):
    return {
        '调拨日期': '2026-01-16',
        '调拨原因': '领用出库测试',
        '调出分公司': '测试分公司',
        '调入分公司': '测试分公司',
        'items': [{'item': item_id('AST-TEST-001'), '数量': 1}],
    }


@pytest.mark.django_db
class TestPurchaseFlow:
    """采购入库流程"""

    def test_purchase_success(self, authenticated_client, purchase_payload, branch):
        resp = authenticated_client.post(_action_url('purchase'), purchase_payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.data
        assert data['lines'][0]['item_code'] == 'AST-TEST-001'
        assert data['lines'][0]['item_name'] == '测试品目 AST-TEST-001'
        assert data['lines'][0]['数量'] == 1
        assert data['品项数'] == 1 and data['总数量'] == 1
        assert data['action_type'] == 'purchase'

    def test_purchase_missing_required_field(self, authenticated_client):
        payload = {
            '调拨日期': '2026-01-15',
            '调出分公司': '测试分公司',
            # missing items
        }
        resp = authenticated_client.post(_action_url('purchase'), payload, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_purchase_unauthenticated(self, api_client, purchase_payload):
        resp = api_client.post(_action_url('purchase'), purchase_payload, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_purchase_listed_in_transfers(self, authenticated_client, purchase_payload, branch):
        authenticated_client.post(_action_url('purchase'), purchase_payload, format='json')
        resp = authenticated_client.get(TRANSFER_LIST_URL, format='json')
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        assert len(results) >= 1


@pytest.mark.django_db
class TestAssignFlow:
    """领用出库流程"""

    def test_assign_success(self, authenticated_client, assign_payload, branch):
        resp = authenticated_client.post(_action_url('assign'), assign_payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.data
        assert data['action_type'] == 'assign'

    def test_assign_missing_to_branch(self, authenticated_client, branch, item_id):
        payload = {
            '调拨日期': '2026-01-16',
            '调出分公司': '测试分公司',
            'items': [{'item': item_id('AST-TEST-002'), '数量': 1}],
        }
        resp = authenticated_client.post(_action_url('assign'), payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestReturnFlow:
    """归还流程"""

    def test_return_success(self, authenticated_client, branch, item_id):
        payload = {
            '调拨日期': '2026-01-17',
            '调拨原因': '归还测试',
            '调入分公司': '测试分公司',
            'items': [{'item': item_id('AST-TEST-001'), '数量': 1}],
        }
        resp = authenticated_client.post(_action_url('return'), payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['action_type'] == 'return'


@pytest.mark.django_db
class TestTransferFlow:
    """调拨流程"""

    def test_transfer_success(self, authenticated_client, branch, second_branch, item_id):
        payload = {
            '调拨日期': '2026-01-18',
            '调拨原因': '调拨测试',
            '调出分公司': branch.name,
            '调入分公司': second_branch.name,
            'items': [{'item': item_id('AST-TEST-001'), '数量': 1}],
        }
        resp = authenticated_client.post(_action_url('transfer'), payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['action_type'] == 'transfer'


@pytest.mark.django_db
class TestRepairScrapRemoved:
    """维修/报废端点已移除，应返回 405"""

    def test_repair_returns_405(self, authenticated_client, item_id):
        payload = {
            '调拨日期': '2026-01-19',
            '调拨原因': '维修测试',
            '调出分公司': '测试分公司',
            'items': [{'item': item_id('AST-TEST-001'), '数量': 1}],
        }
        resp = authenticated_client.post(_action_url('repair'), payload, format='json')
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_scrap_returns_405(self, authenticated_client, item_id):
        payload = {
            '调拨日期': '2026-01-20',
            '调拨原因': '报废测试',
            '调出分公司': '测试分公司',
            'items': [{'item': item_id('AST-TEST-001'), '数量': 1}],
        }
        resp = authenticated_client.post(_action_url('scrap'), payload, format='json')
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestApproveFlow:
    """审批流程"""

    def _create_pending_transfer(self, client, item_id):
        payload = {
            '调拨日期': '2026-01-15',
            '调拨原因': '审批测试',
            '调出分公司': '测试分公司',
            'items': [{'item': item_id('AST-APPROVE-001'), '数量': 1}],
        }
        resp = client.post(_action_url('purchase'), payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        return resp.data['id']

    def test_approve_success(self, authenticated_client, branch, item_id):
        transfer_id = self._create_pending_transfer(authenticated_client, item_id)
        resp = authenticated_client.post(
            _action_url('approve', transfer_id),
            {'approved': True, 'reason': '同意'},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert data['审批状态'] == '已入库'

    def test_reject_success(self, authenticated_client, branch, item_id):
        transfer_id = self._create_pending_transfer(authenticated_client, item_id)
        resp = authenticated_client.post(
            _action_url('approve', transfer_id),
            {'approved': False, 'reason': '不合规'},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert data['审批状态'] == '已驳回'

    def test_approve_missing_decision(self, authenticated_client, branch, item_id):
        transfer_id = self._create_pending_transfer(authenticated_client, item_id)
        resp = authenticated_client.post(
            _action_url('approve', transfer_id),
            {},
            format='json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_approve_nonexistent_transfer(self, authenticated_client):
        resp = authenticated_client.post(
            _action_url('approve', '00000000-0000-0000-0000-000000000000'),
            {'approved': True},
            format='json',
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestTransferList:
    """Transfer list and filtering"""

    def test_list_transfers(self, authenticated_client):
        resp = authenticated_client.get(TRANSFER_LIST_URL, format='json')
        assert resp.status_code == status.HTTP_200_OK

    def test_list_requires_auth(self, api_client):
        resp = api_client.get(TRANSFER_LIST_URL, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_filter_by_action_type(self, authenticated_client, purchase_payload):
        # Create a purchase transfer
        authenticated_client.post(_action_url('purchase'), purchase_payload, format='json')
        # Filter by action_type
        resp = authenticated_client.get(
            f'{TRANSFER_LIST_URL}?action_type=purchase',
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        assert all(t['action_type'] == 'purchase' for t in results)


@pytest.mark.django_db
class TestApproveAssetSync:
    """审批联动台账矩阵（Asset 时代契约已随第三刀退役）。"""

    def _seed_ledger(self, branch, code, stock=5):
        from apps.assets.services import ledger
        from apps.categories.models import Category
        item = Category.objects.get(asset_code=code)
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, stock, '测试造数')
        return item

    def test_assign_approve_moves_ledger(self, authenticated_client, branch, item_id):
        self._seed_ledger(branch, 'AST-SYNC-001')
        payload = {
            '调拨日期': '2026-02-01',
            '调出分公司': branch.name,
            'items': [{'item': item_id('AST-SYNC-001'), '数量': 1}],
        }
        resp = authenticated_client.post(_action_url('assign'), payload, format='json')
        transfer_id = resp.data['id']
        authenticated_client.post(_action_url('approve', transfer_id), {'approved': True}, format='json')

        from apps.assets.models import AssetStock
        row = AssetStock.objects.get(branch=branch, item__asset_code='AST-SYNC-001')
        assert row.在库数量 == 4 and row.在用数量 == 1
        row.refresh_from_db()

    def test_return_approve_moves_ledger(self, authenticated_client, branch, item_id):
        from apps.assets.models import AssetStock
        from apps.assets.services import ledger
        from apps.categories.models import Category
        item = Category.objects.get(asset_code='AST-SYNC-001')
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 5, '造数')
        ledger.apply_adjustment(branch, item, ledger.COLUMN_IN_USE, 3, '造数')
        payload = {
            '调拨日期': '2026-02-02',
            '调入分公司': branch.name,
            'items': [{'item': item_id('AST-SYNC-001'), '数量': 2}],
        }
        resp = authenticated_client.post(_action_url('return'), payload, format='json')
        transfer_id = resp.data['id']
        authenticated_client.post(_action_url('approve', transfer_id), {'approved': True}, format='json')
        row = AssetStock.objects.get(branch=branch, item=item)
        assert row.在用数量 == 1 and row.在库数量 == 7

    def test_transfer_approve_moves_both_ledgers(self, authenticated_client, branch, second_branch, item_id):
        from apps.assets.models import AssetStock
        self._seed_ledger(branch, 'AST-SYNC-001')
        payload = {
            '调拨日期': '2026-02-03',
            '调出分公司': branch.name,
            '调入分公司': second_branch.name,
            'items': [{'item': item_id('AST-SYNC-001'), '数量': 2}],
        }
        resp = authenticated_client.post(_action_url('transfer'), payload, format='json')
        transfer_id = resp.data['id']
        authenticated_client.post(_action_url('approve', transfer_id), {'approved': True}, format='json')
        assert AssetStock.objects.get(branch=branch, item__asset_code='AST-SYNC-001').在库数量 == 3
        assert AssetStock.objects.get(branch=second_branch, item__asset_code='AST-SYNC-001').在库数量 == 2

    def test_reject_does_not_touch_ledger(self, authenticated_client, branch, item_id):
        from apps.assets.models import AssetStock
        self._seed_ledger(branch, 'AST-SYNC-001')
        payload = {
            '调拨日期': '2026-02-04',
            '调出分公司': branch.name,
            'items': [{'item': item_id('AST-SYNC-001'), '数量': 1}],
        }
        resp = authenticated_client.post(_action_url('assign'), payload, format='json')
        transfer_id = resp.data['id']
        authenticated_client.post(
            _action_url('approve', transfer_id),
            {'approved': False, 'reason': '驳回'},
            format='json',
        )
        row = AssetStock.objects.get(branch=branch, item__asset_code='AST-SYNC-001')
        assert row.在库数量 == 5 and row.在用数量 == 0
