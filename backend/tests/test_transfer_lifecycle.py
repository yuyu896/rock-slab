"""五类流转单的草稿、提交、撤回与重提统一行为。"""
import pytest
from django.db.models.query import QuerySet

from conftest import _client_for


ACTION_TYPES = ('purchase', 'assign', 'return', 'transfer', 'recovery')


def _payload(action_type, item_id, branch, second_branch, department):
    item = {'item': item_id('AST-TEST-001'), '数量': 1}
    if action_type == 'purchase':
        return {'调拨日期': '2026-09-19', '调入分公司': branch.name, 'items': [item]}
    if action_type == 'assign':
        item.update({'使用人': '生命周期测试人', 'department': str(department.id)})
        return {'调拨日期': '2026-09-19', '调出分公司': branch.name, 'items': [item]}
    if action_type == 'return':
        return {'调拨日期': '2026-09-19', '调入分公司': branch.name, 'items': [item]}
    if action_type == 'transfer':
        return {
            '调拨日期': '2026-09-19', '调出分公司': branch.name,
            '调入分公司': second_branch.name, 'items': [item],
        }
    return {
        '调拨日期': '2026-09-19', '调出分公司': branch.name,
        '回收去向': 'dispose', '处置方式': '报废', 'items': [item],
    }


def _prepare_recovery_stock(action_type, branch, item_id):
    if action_type != 'recovery':
        return None
    from apps.assets.models import AssetStock
    from apps.assets.services import ledger
    from apps.categories.models import Category

    item = Category.objects.get(pk=item_id('AST-TEST-001'))
    ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 5, '流转生命周期测试造数')
    return AssetStock.objects.get(branch=branch, item=item)


def _create(client, action_type, payload, *, draft=False):
    payload = {**payload, 'draft': draft}
    response = client.post(f'/api/transfers/{action_type}', payload, format='json')
    assert response.status_code == 201, response.data
    return response


def _stock_snapshot():
    from apps.assets.models import AssetStock
    return list(AssetStock.objects.order_by('id').values_list('id', '在库数量', '在用数量'))


def _ledger_snapshot():
    from apps.assets.models import LedgerAdjustment
    return list(LedgerAdjustment.objects.order_by('id').values_list('id',))


@pytest.mark.django_db
@pytest.mark.parametrize('action_type', ACTION_TYPES)
def test_all_action_types_save_complete_draft_without_effects(
    action_type, admin_user, branch, second_branch, department, item_id,
):
    from apps.notifications.models import Notification

    _prepare_recovery_stock(action_type, branch, item_id)
    before_stock = _stock_snapshot()
    before_ledger = _ledger_snapshot()
    client = _client_for(admin_user)

    response = _create(
        client, action_type,
        _payload(action_type, item_id, branch, second_branch, department),
        draft=True,
    )

    assert response.data['审批状态'] == '草稿'
    assert response.data['lines']
    assert not Notification.objects.filter(
        related_object_type='transfer', related_object_id=response.data['id'],
    ).exists()
    assert _stock_snapshot() == before_stock
    assert _ledger_snapshot() == before_ledger


@pytest.mark.django_db
@pytest.mark.parametrize('action_type', ACTION_TYPES)
def test_all_action_types_reject_draft_without_valid_lines(
    action_type, admin_user, branch, second_branch, department, item_id,
):
    from apps.transfers.models import Transfer

    payload = _payload(action_type, item_id, branch, second_branch, department)
    payload['items'] = []
    response = _client_for(admin_user).post(
        f'/api/transfers/{action_type}', {**payload, 'draft': True}, format='json',
    )

    assert response.status_code == 400
    assert Transfer.objects.filter(action_type=action_type).count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize('action_type', ACTION_TYPES)
def test_creator_can_withdraw_each_pending_type_without_ledger_or_notification_effects(
    action_type, admin_user, branch, second_branch, department, item_id,
):
    from apps.notifications.models import Notification
    from apps.transfers.models import Transfer

    _prepare_recovery_stock(action_type, branch, item_id)
    client = _client_for(admin_user)
    response = _create(
        client, action_type,
        _payload(action_type, item_id, branch, second_branch, department),
    )
    transfer_id = response.data['id']
    notification_count = Notification.objects.filter(
        related_object_type='transfer', related_object_id=transfer_id,
    ).count()
    before_stock = _stock_snapshot()
    before_ledger = _ledger_snapshot()

    response = client.post(f'/api/transfers/{transfer_id}/withdraw', format='json')

    assert response.status_code == 200, response.data
    assert response.data['审批状态'] == '草稿'
    assert Transfer.objects.get(pk=transfer_id).审批状态 == '草稿'
    assert Notification.objects.filter(
        related_object_type='transfer', related_object_id=transfer_id,
    ).count() == notification_count
    assert _stock_snapshot() == before_stock
    assert _ledger_snapshot() == before_ledger


@pytest.mark.django_db
@pytest.mark.parametrize('action_type', ACTION_TYPES)
def test_non_creator_cannot_withdraw_each_pending_type(
    action_type, admin_user, branch, second_branch, department, item_id,
):
    from django.contrib.auth import get_user_model
    from apps.transfers.models import Transfer

    _prepare_recovery_stock(action_type, branch, item_id)
    other = get_user_model().objects.create_user(
        phone='13900000091', name='非创建人', password='test123456',
        role='admin', status='active',
    )
    response = _create(
        _client_for(admin_user), action_type,
        _payload(action_type, item_id, branch, second_branch, department),
    )
    transfer_id = response.data['id']

    response = _client_for(other).post(f'/api/transfers/{transfer_id}/withdraw', format='json')

    assert response.status_code == 400
    assert '创建人' in response.data['detail']
    assert Transfer.objects.get(pk=transfer_id).审批状态 == '待审批'


@pytest.mark.django_db
@pytest.mark.parametrize('action_type', ACTION_TYPES)
def test_all_action_types_support_submit_reject_and_resubmit_without_ledger_effects(
    action_type, admin_user, branch, second_branch, department, item_id,
):
    client = _client_for(admin_user)
    _prepare_recovery_stock(action_type, branch, item_id)
    before_stock = _stock_snapshot()
    response = _create(
        client, action_type,
        _payload(action_type, item_id, branch, second_branch, department),
        draft=True,
    )
    transfer_id = response.data['id']

    response = client.post(f'/api/transfers/{transfer_id}/submit', format='json')
    assert response.status_code == 200, response.data
    assert response.data['审批状态'] == '待审批'

    response = client.post(
        f'/api/transfers/{transfer_id}/approve', {'approved': False}, format='json',
    )
    assert response.status_code == 200, response.data
    assert response.data['审批状态'] == '已驳回'

    response = client.post(f'/api/transfers/{transfer_id}/resubmit', format='json')
    assert response.status_code == 200, response.data
    assert response.data['审批状态'] == '待审批'
    assert _stock_snapshot() == before_stock


@pytest.mark.django_db
@pytest.mark.parametrize('action_type', ACTION_TYPES)
def test_can_withdraw_is_computed_for_list_and_detail_for_all_types(
    action_type, admin_user, branch, second_branch, department, item_id,
):
    from apps.transfers.models import Transfer

    _prepare_recovery_stock(action_type, branch, item_id)
    client = _client_for(admin_user)
    response = _create(
        client, action_type,
        _payload(action_type, item_id, branch, second_branch, department),
    )
    transfer_id = response.data['id']

    detail = client.get(f'/api/transfers/{transfer_id}', format='json')
    assert detail.status_code == 200
    assert detail.data['canWithdraw'] is True

    listing = client.get('/api/transfers/', {'type': action_type}, format='json')
    assert listing.status_code == 200
    rows = listing.data.get('results', listing.data)
    row = next(item for item in rows if item['id'] == transfer_id)
    assert row['canWithdraw'] is True

    assert client.post(f'/api/transfers/{transfer_id}/withdraw', format='json').status_code == 200
    detail = client.get(f'/api/transfers/{transfer_id}', format='json')
    assert detail.data['canWithdraw'] is False
    assert Transfer.objects.get(pk=transfer_id).审批状态 == '草稿'


@pytest.mark.django_db
@pytest.mark.parametrize('action_type', ACTION_TYPES)
@pytest.mark.parametrize('document_status', ('草稿', '已驳回'))
def test_can_edit_draft_allows_owner_and_admin_but_not_other_staff(
    action_type, document_status, admin_user, staff_user, branch, second_branch,
    department, item_id, db,
):
    from django.contrib.auth import get_user_model

    _prepare_recovery_stock(action_type, branch, item_id)
    owner_client = _client_for(admin_user)
    response = _create(
        owner_client, action_type,
        _payload(action_type, item_id, branch, second_branch, department),
        draft=document_status == '草稿',
    )
    transfer_id = response.data['id']
    if document_status == '已驳回':
        rejected = owner_client.post(
            f'/api/transfers/{transfer_id}/approve',
            {'approved': False}, format='json',
        )
        assert rejected.status_code == 200

    owner_detail = owner_client.get(f'/api/transfers/{transfer_id}', format='json')
    assert owner_detail.data['canEditDraft'] is True

    other_admin = get_user_model().objects.create_user(
        phone='13900000092', name='另一管理员', password='test123456',
        role='admin', status='active',
    )
    admin_detail = _client_for(other_admin).get(
        f'/api/transfers/{transfer_id}', format='json',
    )
    assert admin_detail.data['canEditDraft'] is True

    staff_detail = _client_for(staff_user).get(
        f'/api/transfers/{transfer_id}', format='json',
    )
    assert staff_detail.status_code == 200
    assert staff_detail.data['canEditDraft'] is False


@pytest.mark.django_db
def test_can_edit_transfer_draft_requires_operable_source_scope(
    admin_user, staff_b, branch, second_branch, department, item_id,
):
    from apps.transfers.models import Transfer

    client = _client_for(admin_user)
    response = _create(
        client, 'transfer',
        _payload('transfer', item_id, branch, second_branch, department),
        draft=True,
    )
    transfer_id = response.data['id']
    # 模拟单据创建人后来只有调入方范围；记录对其可见，但不能操作调出方。
    Transfer.objects.filter(pk=transfer_id).update(created_by=staff_b)

    detail = _client_for(staff_b).get(f'/api/transfers/{transfer_id}', format='json')

    assert detail.status_code == 200
    assert detail.data['canEditDraft'] is False


@pytest.mark.django_db
def test_transfer_creator_without_source_scope_cannot_withdraw(
    admin_user, staff_b, branch, second_branch, department, item_id,
):
    from apps.transfers.models import Transfer

    response = _create(
        _client_for(admin_user), 'transfer',
        _payload('transfer', item_id, branch, second_branch, department),
    )
    transfer_id = response.data['id']
    Transfer.objects.filter(pk=transfer_id).update(created_by=staff_b)

    client = _client_for(staff_b)
    detail = client.get(f'/api/transfers/{transfer_id}', format='json')

    assert detail.status_code == 200
    assert detail.data['canWithdraw'] is False
    assert client.post(f'/api/transfers/{transfer_id}/withdraw', format='json').status_code == 400


@pytest.mark.django_db
def test_mine_filter_uses_created_by_account_not_display_name_or_client_input(
    branch, second_branch, department, item_id,
):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    first_user = User.objects.create_user(
        phone='13900000093', name='同名创建人', password='test123456',
        role='admin', status='active',
    )
    second_user = User.objects.create_user(
        phone='13900000094', name='同名创建人', password='test123456',
        role='admin', status='active',
    )
    payload = _payload('purchase', item_id, branch, second_branch, department)
    first = _create(_client_for(first_user), 'purchase', payload)
    # 创建人文本可由客户端提供，但权限与 mine 筛选必须使用认证账号外键。
    second_payload = {**payload, '创建人': first_user.name}
    second = _create(_client_for(second_user), 'purchase', second_payload)

    first_list = _client_for(first_user).get(
        '/api/transfers/', {'type': 'purchase', 'mine': 'TRUE'}, format='json',
    )
    second_list = _client_for(second_user).get(
        '/api/transfers/', {'type': 'purchase', 'mine': 'true'}, format='json',
    )

    first_rows = first_list.data.get('results', first_list.data)
    second_rows = second_list.data.get('results', second_list.data)
    assert {row['id'] for row in first_rows} == {first.data['id']}
    assert {row['id'] for row in second_rows} == {second.data['id']}


@pytest.mark.django_db
def test_withdraw_rechecks_state_after_lock_when_approval_wins_race(
    admin_user, branch, second_branch, department, item_id, monkeypatch,
):
    from apps.transfers.models import Transfer

    client = _client_for(admin_user)
    response = _create(
        client, 'assign',
        _payload('assign', item_id, branch, second_branch, department),
    )
    transfer_id = response.data['id']
    original_get = QuerySet.get

    def approve_before_locked_read(queryset, *args, **kwargs):
        if queryset.query.select_for_update and str(kwargs.get('pk')) == transfer_id:
            Transfer.objects.filter(pk=transfer_id).update(审批状态='已通过')
        return original_get(queryset, *args, **kwargs)

    monkeypatch.setattr(QuerySet, 'get', approve_before_locked_read)
    response = client.post(f'/api/transfers/{transfer_id}/withdraw', format='json')

    assert response.status_code == 400
    assert '已处理' in response.data['detail']
    assert Transfer.objects.get(pk=transfer_id).审批状态 == '已通过'
