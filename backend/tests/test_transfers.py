"""
Tests for Transfer flow: purchase, assign, return, transfer, repair, scrap, approve.
"""
import pytest
from django.urls import reverse
from rest_framework import status

TRANSFER_LIST_URL = '/api/transfers/'


def _action_url(action_name, pk=None):
    if pk:
        return f'/api/transfers/{pk}/{action_name}'
    return f'/api/transfers/{action_name}'


@pytest.fixture
def purchase_payload():
    return {
        '调拨日期': '2026-01-15',
        '资产编号': 'AST-TEST-001',
        '资产名称': '测试资产',
        '调拨数量': 1,
        '调拨原因': '采购入库测试',
        '调出分公司': '测试分公司',
        'action_type': 'purchase',
    }


@pytest.fixture
def assign_payload():
    return {
        '调拨日期': '2026-01-16',
        '资产编号': 'AST-TEST-001',
        '资产名称': '测试资产',
        '调拨数量': 1,
        '调拨原因': '领用出库测试',
        '调出分公司': '测试分公司',
        '调入分公司': '测试分公司',
        'action_type': 'assign',
    }


@pytest.mark.django_db
class TestPurchaseFlow:
    """采购入库流程"""

    def test_purchase_success(self, authenticated_client, purchase_payload):
        resp = authenticated_client.post(_action_url('purchase'), purchase_payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.data
        assert data['资产编号'] == 'AST-TEST-001'
        assert data['资产名称'] == '测试资产'
        assert data['action_type'] == 'purchase'

    def test_purchase_missing_required_field(self, authenticated_client):
        payload = {
            '调拨日期': '2026-01-15',
            # missing 资产编号 and 资产名称
        }
        resp = authenticated_client.post(_action_url('purchase'), payload, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_purchase_unauthenticated(self, api_client, purchase_payload):
        resp = api_client.post(_action_url('purchase'), purchase_payload, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_purchase_listed_in_transfers(self, authenticated_client, purchase_payload):
        authenticated_client.post(_action_url('purchase'), purchase_payload, format='json')
        resp = authenticated_client.get(TRANSFER_LIST_URL, format='json')
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        assert len(results) >= 1


@pytest.mark.django_db
class TestAssignFlow:
    """领用出库流程"""

    def test_assign_success(self, authenticated_client, assign_payload):
        resp = authenticated_client.post(_action_url('assign'), assign_payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.data
        assert data['action_type'] == 'assign'

    def test_assign_missing_to_branch(self, authenticated_client):
        payload = {
            '调拨日期': '2026-01-16',
            '资产编号': 'AST-TEST-002',
            '资产名称': '测试资产2',
            'action_type': 'assign',
        }
        resp = authenticated_client.post(_action_url('assign'), payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestReturnFlow:
    """归还流程"""

    def test_return_success(self, authenticated_client):
        payload = {
            '调拨日期': '2026-01-17',
            '资产编号': 'AST-TEST-001',
            '资产名称': '测试资产',
            '调拨数量': 1,
            '调拨原因': '归还测试',
            '调入分公司': '测试分公司',
            'action_type': 'return',
        }
        resp = authenticated_client.post(_action_url('return'), payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['action_type'] == 'return'


@pytest.mark.django_db
class TestTransferFlow:
    """调拨流程"""

    def test_transfer_success(self, authenticated_client):
        payload = {
            '调拨日期': '2026-01-18',
            '资产编号': 'AST-TEST-001',
            '资产名称': '测试资产',
            '调拨数量': 1,
            '调拨原因': '调拨测试',
            '调出分公司': '测试分公司',
            '调入分公司': '测试分公司',
            'action_type': 'transfer',
        }
        resp = authenticated_client.post(_action_url('transfer'), payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['action_type'] == 'transfer'


@pytest.mark.django_db
class TestRepairFlow:
    """维修流程"""

    def test_repair_success(self, authenticated_client):
        payload = {
            '调拨日期': '2026-01-19',
            '资产编号': 'AST-TEST-001',
            '资产名称': '测试资产',
            '调拨数量': 1,
            '调拨原因': '维修测试',
            '调出分公司': '测试分公司',
            'action_type': 'repair',
        }
        resp = authenticated_client.post(_action_url('repair'), payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['action_type'] == 'repair'


@pytest.mark.django_db
class TestScrapFlow:
    """报废流程"""

    def test_scrap_success(self, authenticated_client):
        payload = {
            '调拨日期': '2026-01-20',
            '资产编号': 'AST-TEST-001',
            '资产名称': '测试资产',
            '调拨数量': 1,
            '调拨原因': '报废测试',
            '调出分公司': '测试分公司',
            'action_type': 'scrap',
        }
        resp = authenticated_client.post(_action_url('scrap'), payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['action_type'] == 'scrap'


@pytest.mark.django_db
class TestApproveFlow:
    """审批流程"""

    def _create_pending_transfer(self, client):
        payload = {
            '调拨日期': '2026-01-15',
            '资产编号': 'AST-APPROVE-001',
            '资产名称': '审批测试资产',
            '调拨数量': 1,
            '调拨原因': '审批测试',
            '调出分公司': '测试分公司',
            'action_type': 'purchase',
        }
        resp = client.post(_action_url('purchase'), payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        return resp.data['id']

    def test_approve_success(self, authenticated_client):
        transfer_id = self._create_pending_transfer(authenticated_client)
        resp = authenticated_client.post(
            _action_url('approve', transfer_id),
            {'approved': True, 'reason': '同意'},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert data['审批状态'] == '已通过'

    def test_reject_success(self, authenticated_client):
        transfer_id = self._create_pending_transfer(authenticated_client)
        resp = authenticated_client.post(
            _action_url('approve', transfer_id),
            {'approved': False, 'reason': '不合规'},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert data['审批状态'] == '已驳回'

    def test_approve_missing_decision(self, authenticated_client):
        transfer_id = self._create_pending_transfer(authenticated_client)
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
