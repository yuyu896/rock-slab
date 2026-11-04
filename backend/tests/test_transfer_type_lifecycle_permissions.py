import pytest
from rest_framework import status

from apps.permissions.models import ManagementScope, OperationGrant


def _user(phone, name, branch, *operations, role='staff', scope_branch=None, scope_region=None):
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create_user(
        phone=phone, name=name, password='test123456',
        role=role, status='active', branch=branch,
    )
    if scope_region:
        ManagementScope.objects.create(user=user, region=scope_region)
    else:
        ManagementScope.objects.create(user=user, branch=scope_branch or branch)
    for code in operations:
        OperationGrant.objects.create(user=user, code=code)
    return user


def _client(user):
    from conftest import _client_for

    return _client_for(user)


def _purchase(client, branch, *, draft=False):
    from apps.categories.models import Category

    item, _ = Category.objects.get_or_create(
        asset_code='TYPE-PERMISSION-ITEM',
        defaults={
            'asset_category': '权限测试', 'item_category': '办公',
            'asset_name': '权限测试品目', 'unit': '台',
            'management_type': 'ledger',
        },
    )
    response = client.post('/api/transfers/purchase', {
        '调拨日期': '2026-10-22',
        '调入分公司': branch.name,
        'draft': draft,
        'items': [{'item': str(item.id), '数量': 1}],
    }, format='json')
    assert response.status_code == status.HTTP_201_CREATED, response.data
    return response.data['id']


def _recovery(client, branch, item, *, draft=True, destination='dispose'):
    return client.post('/api/transfers/recovery', {
        '调拨日期': '2026-10-22',
        '调出分公司': branch.name,
        '回收去向': destination,
        '处置方式': '报废' if destination == 'dispose' else '',
        'draft': draft,
        'items': [{'item': str(item.id), '数量': 1}],
    }, format='json')


def _recovery_stock(branch, item):
    from apps.assets.services import ledger

    ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 10, '直接处置权限测试造数')


@pytest.mark.django_db
def test_purchase_edit_permission_covers_create_edit_and_submit(branch):
    from apps.transfers.models import Transfer

    user = _user('13966000001', '采购制单人', branch, 'edit_purchase', 'view_categories')
    client = _client(user)
    denied = client.post('/api/transfers/purchase', {
        '调拨日期': '2026-10-22', '调入分公司': branch.name,
        'draft': True, 'items': [{'item': '00000000-0000-0000-0000-000000000000', '数量': 1}],
    }, format='json')
    assert denied.status_code == status.HTTP_403_FORBIDDEN
    OperationGrant.objects.create(user=user, code='view_purchase')
    transfer_id = _purchase(client, branch, draft=True)

    url = f'/api/transfers/{transfer_id}'
    assert client.get(url).status_code == status.HTTP_200_OK
    response = client.patch(url, {'备注': '补充信息'}, format='json')
    assert response.status_code == status.HTTP_200_OK, response.data

    OperationGrant.objects.filter(user=user, code='edit_purchase').delete()
    response = client.post(f'{url}/submit', {}, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN

    OperationGrant.objects.create(user=user, code='edit_purchase')
    response = client.post(f'{url}/submit', {}, format='json')
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data['审批状态'] == '待审批'
    assert Transfer.objects.get(pk=transfer_id).审批状态 == '待审批'


@pytest.mark.django_db
def test_purchase_edit_permission_covers_draft_and_immediate_submission(branch):
    from apps.transfers.models import Transfer

    user = _user('13966000011', '采购编辑权限用户', branch, 'edit_purchase', 'view_categories')
    client = _client(user)
    OperationGrant.objects.create(user=user, code='view_purchase')
    draft_id = _purchase(client, branch, draft=True)
    draft = Transfer.objects.get(pk=draft_id)
    payload = {
        '调拨日期': '2026-10-22',
        '调入分公司': branch.name,
        'items': [{'item': str(draft.lines.first().item_id), '数量': 1}],
    }
    response = client.post('/api/transfers/purchase', payload, format='json')
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data['审批状态'] == '待审批'
    assert Transfer.objects.count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize(('phone', 'route', 'edit_code', 'view_code', 'option_code'), [
    ('13966000021', 'purchase', 'edit_purchase', 'view_purchase', 'view_categories'),
    ('13966000022', 'assign', 'edit_assignment', 'view_assignment', 'view_asset_ledger'),
    ('13966000024', 'transfer', 'edit_transfer', 'view_transfer', 'view_asset_ledger'),
])
def test_document_creation_requires_edit_and_view_prerequisites(
    branch, category, phone, route, edit_code, view_code, option_code,
):
    from apps.transfers.models import Transfer

    user = _user(phone, '单据编辑权限测试', branch, edit_code, option_code)
    response = _client(user).post(f'/api/transfers/{route}', {
        '调拨日期': '2026-10-22',
        '调出分公司': branch.name,
        '调入分公司': branch.name,
        'items': [{'item': str(category.id), '数量': 1}],
    }, format='json')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert not Transfer.objects.exists()

    OperationGrant.objects.create(user=user, code=view_code)
    response = _client(user).post(f'/api/transfers/{route}', {
        '调拨日期': '2026-10-22',
        '调出分公司': branch.name,
        '调入分公司': branch.name,
        'items': [{'item': str(category.id), '数量': 1}],
    }, format='json')
    if route == 'assign' and response.status_code == status.HTTP_400_BAD_REQUEST:
        # The fixture item is instance-managed and the form payload intentionally
        # omits an instance binding; reaching validation proves permissions passed.
        assert 'INSTANCE_INVALID' in str(response.data)
    else:
        assert response.status_code == status.HTTP_201_CREATED, response.data


@pytest.mark.django_db
@pytest.mark.parametrize(('phone', 'route', 'edit_code', 'view_code', 'read_code'), [
    ('13966000101', 'purchase', 'edit_purchase', 'view_purchase', 'view_categories'),
    ('13966000102', 'assign', 'edit_assignment', 'view_assignment', 'view_asset_ledger'),
    ('13966000104', 'transfer', 'edit_transfer', 'view_transfer', 'view_asset_ledger'),
    ('13966000105', 'recovery', 'edit_recovery', 'view_recovery', 'view_asset_ledger'),
])
def test_document_creation_requires_its_option_read_permission(
    branch, category, department, phone, route, edit_code, view_code, read_code,
):
    from apps.transfers.models import Transfer

    user = _user(phone, '建单查看依赖测试', branch, edit_code, view_code)
    client = _client(user)
    before_count = Transfer.objects.count()
    item = {'item': str(category.id), '数量': 1}
    payload = {
        '调拨日期': '2026-10-22',
        '调出分公司': branch.name,
        '调入分公司': branch.name,
        'draft': True,
        'items': [item],
    }
    if route == 'assign':
        item.update({'使用人': '测试使用人', 'department': str(department.id)})
    if route == 'recovery':
        _recovery_stock(branch, category)
        payload.update({'回收去向': 'dispose', '处置方式': '报废'})

    denied = client.post(f'/api/transfers/{route}', payload, format='json')
    assert denied.status_code == status.HTTP_403_FORBIDDEN
    assert Transfer.objects.count() == before_count

    OperationGrant.objects.create(user=user, code=read_code)
    allowed = client.post(f'/api/transfers/{route}', payload, format='json')
    if route == 'assign' and allowed.status_code == status.HTTP_400_BAD_REQUEST:
        assert 'INSTANCE_INVALID' in str(allowed.data)
    else:
        assert allowed.status_code == status.HTTP_201_CREATED, allowed.data


@pytest.mark.django_db
def test_generic_transfer_create_endpoint_is_disabled(branch):
    from apps.transfers.models import Transfer

    user = _user('13966000012', '通用单据创建入口测试', branch, 'edit_purchase', 'view_purchase', 'view_categories')
    response = _client(user).post('/api/transfers/', {
        'action_type': Transfer.ACTION_PURCHASE,
        '调拨日期': '2026-10-22',
        '审批状态': '已入库',
        'from_branch': str(branch.id),
    }, format='json')

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert not Transfer.objects.exists()


@pytest.mark.django_db
def test_purchase_edit_permission_covers_creator_withdrawal(branch):
    user = _user('13966000002', '采购撤回人', branch, 'edit_purchase', 'view_purchase', 'view_categories')
    client = _client(user)
    transfer_id = _purchase(client, branch)
    url = f'/api/transfers/{transfer_id}/withdraw'

    response = client.post(url, {}, format='json')
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data['审批状态'] == '草稿'


@pytest.mark.django_db
def test_recovery_ledger_requires_its_grant_and_respects_scope(branch, second_branch, category):
    from apps.transfers.models import Transfer

    _recovery_stock(branch, category)
    user = _user(
        '13966000010', '回收台账测试人', branch,
        'edit_recovery', 'view_recovery', 'view_asset_ledger',
    )
    client = _client(user)
    response = _recovery(client, branch, category)
    assert response.status_code == status.HTTP_201_CREATED, response.data
    transfer = Transfer.objects.get(pk=response.data['id'])
    transfer.审批状态 = '已通过'
    transfer.save(update_fields=['审批状态'])

    assert client.get('/api/transfers/recovery-ledger').status_code == status.HTTP_403_FORBIDDEN
    assert client.get('/api/transfers/recovery-ledger/export').status_code == status.HTTP_403_FORBIDDEN

    OperationGrant.objects.create(user=user, code='view_recovery_ledger')
    ledger = client.get('/api/transfers/recovery-ledger')
    assert ledger.status_code == status.HTTP_200_OK, ledger.data
    assert ledger.data['count'] == 1

    ManagementScope.objects.filter(user=user).delete()
    ManagementScope.objects.create(user=user, branch=second_branch)
    scoped_ledger = client.get('/api/transfers/recovery-ledger')
    assert scoped_ledger.status_code == status.HTTP_200_OK, scoped_ledger.data
    assert scoped_ledger.data['count'] == 0


@pytest.mark.django_db
def test_import_requires_combined_edit_and_view_prerequisites(branch):
    from django.core.files.uploadedfile import SimpleUploadedFile

    user = _user('13966000003', '采购导入权限用户', branch, 'edit_purchase', 'view_purchase')
    client = _client(user)
    upload = SimpleUploadedFile('invalid.xlsx', b'not an xlsx file')

    response = client.post(
        '/api/transfers/import?type=purchase', {'file': upload}, format='multipart',
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    OperationGrant.objects.create(user=user, code='view_categories')
    upload = SimpleUploadedFile('invalid.xlsx', b'not an xlsx file')
    response = client.post(
        '/api/transfers/import?type=purchase', {'file': upload}, format='multipart',
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_import_template_requires_combined_edit_and_view_prerequisites(branch):
    user = _user('13966000005', '采购模板权限用户', branch, 'edit_purchase', 'view_purchase')
    client = _client(user)

    response = client.get('/api/transfers/template?type=purchase')
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = client.get('/api/transfers/template?type=unknown')
    assert response.status_code == status.HTTP_403_FORBIDDEN

    OperationGrant.objects.create(user=user, code='view_categories')
    response = client.get('/api/transfers/template?type=purchase')
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.parametrize(('export_type', 'view_code'), [
    ('purchase', 'view_purchase'),
    ('assign', 'view_assignment'),
    ('transfer', 'view_transfer'),
    ('recovery', 'view_recovery'),
])
def test_transfer_export_requires_matching_view_permission(branch, export_type, view_code):
    user = _user('13966000010', 'Transfer export view grant', branch)
    client = _client(user)

    response = client.get('/api/transfers/export', {'type': export_type})
    assert response.status_code == status.HTTP_403_FORBIDDEN

    OperationGrant.objects.create(user=user, code=view_code)
    response = client.get('/api/transfers/export', {'type': export_type})
    assert response.status_code == status.HTTP_200_OK, response.data


@pytest.mark.django_db
def test_retired_return_export_is_not_granted_by_historical_permission(branch):
    user = _user('13966000019', '历史归还权限用户', branch, 'view_return')
    assert _client(user).get('/api/transfers/export', {'type': 'return'}).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.parametrize(('export_type', 'operation_code'), [
    ('purchase', 'edit_purchase'),
    ('purchase', 'approve_purchase'),
    ('assign', 'edit_assignment'),
    ('assign', 'approve_assignment'),
    ('transfer', 'edit_transfer'),
    ('transfer', 'approve_internal_transfer'),
    ('recovery', 'edit_recovery'),
    ('recovery', 'approve_recovery'),
])
def test_transfer_export_is_not_granted_by_create_or_approval_permission(
    branch, export_type, operation_code,
):
    user = _user('13966000012', 'Transfer export non-view grant', branch, operation_code)

    response = _client(user).get('/api/transfers/export', {'type': export_type})

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_transfer_export_does_not_expose_creator_drafts_without_view_permission(branch):
    user = _user('13966000013', 'Transfer creator only', branch, 'edit_purchase', 'view_purchase', 'view_categories')
    client = _client(user)
    transfer_id = _purchase(client, branch, draft=True)
    OperationGrant.objects.filter(user=user, code='view_purchase').delete()

    response = client.get('/api/transfers/export', {'type': 'purchase'})

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_admin_export_hides_another_users_drafts(branch, admin_user):
    import io

    import openpyxl

    owner = _user(
        '13966000023', '草稿所有人', branch,
        'edit_purchase', 'view_purchase', 'view_categories',
    )
    owner_client = _client(owner)
    _purchase(owner_client, branch, draft=True)

    admin_response = _client(admin_user).get(
        '/api/transfers/export', {'type': 'purchase'},
    )
    owner_response = owner_client.get(
        '/api/transfers/export', {'type': 'purchase'},
    )

    assert admin_response.status_code == status.HTTP_200_OK
    assert owner_response.status_code == status.HTTP_200_OK
    admin_rows = list(openpyxl.load_workbook(io.BytesIO(admin_response.content)).active.values)
    owner_rows = list(openpyxl.load_workbook(io.BytesIO(owner_response.content)).active.values)
    assert len(admin_rows) == 1
    assert len(owner_rows) == 2


@pytest.mark.django_db
def test_transfer_export_defaults_to_transfer_and_rejects_unknown_type(branch, admin_user):
    user = _user('13966000014', 'Default transfer export view', branch, 'view_transfer')
    client = _client(user)

    assert client.get('/api/transfers/export').status_code == status.HTTP_200_OK
    assert client.get('/api/transfers/export', {'type': 'unknown'}).status_code == status.HTTP_400_BAD_REQUEST
    assert _client(admin_user).get(
        '/api/transfers/export', {'type': 'unknown'},
    ).status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_pending_documents_cannot_be_deleted(admin_user, branch):
    from apps.transfers.models import Transfer

    transfer_id = _purchase(_client(admin_user), branch, draft=False)
    response = _client(admin_user).delete(f'/api/transfers/{transfer_id}')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['detail'] == '仅草稿可删除'
    assert Transfer.objects.filter(pk=transfer_id).exists()


@pytest.mark.django_db
def test_direct_disposal_creation_uses_recovery_edit_permission(branch, category):
    _recovery_stock(branch, category)
    user = _user('13966000006', '回收制单人', branch)
    client = _client(user)

    response = _recovery(client, branch, category)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    OperationGrant.objects.create(user=user, code='edit_recovery')
    OperationGrant.objects.create(user=user, code='view_recovery')
    OperationGrant.objects.create(user=user, code='view_asset_ledger')
    response = _recovery(client, branch, category)
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data['回收去向'] == 'dispose'

    response = _recovery(client, branch, category, draft=False)
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data['审批状态'] == '待审批'


@pytest.mark.django_db
def test_legacy_disposal_grant_does_not_grant_recovery_creation(branch, category):
    _recovery_stock(branch, category)
    user = _user('13966000015', '仅有旧处置权限', branch, 'dispose_assets')

    response = _recovery(_client(user), branch, category)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_direct_disposal_edit_permission_covers_lifecycle(branch, category):
    from apps.transfers.models import Transfer

    _recovery_stock(branch, category)
    user = _user(
        '13966000007', '回收编辑人', branch,
        'edit_recovery', 'view_recovery', 'view_asset_ledger',
    )
    client = _client(user)
    response = _recovery(client, branch, category)
    assert response.status_code == status.HTTP_201_CREATED, response.data
    transfer_id = response.data['id']
    url = f'/api/transfers/{transfer_id}'

    OperationGrant.objects.filter(user=user, code='edit_recovery').delete()
    response = client.patch(url, {'备注': '补充说明'}, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN

    OperationGrant.objects.create(user=user, code='edit_recovery')
    response = client.patch(url, {'备注': '补充说明'}, format='json')
    assert response.status_code == status.HTTP_200_OK, response.data
    response = client.post(f'{url}/submit', {}, format='json')
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data['审批状态'] == '待审批'
    assert not OperationGrant.objects.filter(user=user, code='dispose_assets').exists()


@pytest.mark.django_db
def test_recovery_approval_uses_role_scope_and_view_prerequisite(branch, second_branch, category):
    _recovery_stock(branch, category)
    owner = _user(
        '13966000008', '回收提交人', branch,
        'edit_recovery', 'view_recovery', 'view_asset_ledger', 'approve_recovery',
        role='manager',
    )
    approver = _user('13966000009', '回收审批人', branch, 'approve_recovery', 'view_recovery', role='leader')
    owner_client = _client(owner)
    response = _recovery(owner_client, branch, category)
    assert response.status_code == status.HTTP_201_CREATED, response.data
    transfer_id = response.data['id']
    response = owner_client.post(f'/api/transfers/{transfer_id}/submit', {}, format='json')
    assert response.status_code == status.HTTP_200_OK, response.data

    response = owner_client.post(
        f'/api/transfers/{transfer_id}/approve', {'approved': True}, format='json',
    )
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data['审批状态'] == '已通过'

    # A peer manager cannot approve this document; no per-document approver
    # assignment is needed for a leader with matching data scope.
    response = _recovery(owner_client, branch, category)
    assert response.status_code == status.HTTP_201_CREATED, response.data
    second_id = response.data['id']
    assert owner_client.post(f'/api/transfers/{second_id}/submit', {}, format='json').status_code == status.HTTP_200_OK
    manager = _user('13966000016', '范围内行政', branch, 'approve_recovery', 'view_recovery', role='manager')
    manager_response = _client(manager).post(
        f'/api/transfers/{second_id}/approve', {'approved': True}, format='json',
    )
    assert manager_response.status_code == status.HTTP_403_FORBIDDEN

    approver_client = _client(approver)
    leader_response = approver_client.post(
        f'/api/transfers/{second_id}/approve', {'approved': True}, format='json',
    )
    assert leader_response.status_code == status.HTTP_200_OK, leader_response.data

    response = _recovery(owner_client, branch, category)
    assert response.status_code == status.HTTP_201_CREATED, response.data
    out_of_scope_id = response.data['id']
    assert owner_client.post(
        f'/api/transfers/{out_of_scope_id}/submit', {}, format='json',
    ).status_code == status.HTTP_200_OK
    out_of_scope_leader = _user(
        '13966000017', '范围外组长', second_branch,
        'approve_recovery', 'view_recovery', role='leader',
    )
    assert _client(out_of_scope_leader).post(
        f'/api/transfers/{out_of_scope_id}/approve', {'approved': True}, format='json',
    ).status_code == status.HTTP_404_NOT_FOUND
