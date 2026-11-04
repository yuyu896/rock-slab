import pytest
from rest_framework import status

from apps.audit.models import AuditLog
from apps.permissions.models import ManagementScope, OperationGrant
from apps.permissions.operations import OPERATION_CATALOG, PAGE_ACCESS_OPERATIONS
from apps.users.models import User
from conftest import _client_for


def _employee(phone, name, branch=None, role='manager'):
    return User.objects.create_user(
        phone=phone, name=name, password='test123456', role=role, branch=branch,
    )


@pytest.mark.django_db
def test_operation_catalog_returns_module_metadata(branch):
    employee = _employee('13920000022', '权限目录员工', branch=branch)

    response = _client_for(employee).get('/api/permissions/operations')

    assert response.status_code == status.HTTP_200_OK
    assert all(item.get('module') and item.get('module_label') for item in response.data)
    assert all(item.get('catalog_version') == 2 for item in response.data)
    assert all('prerequisites' in item and 'conditional_prerequisites' in item for item in response.data)
    catalog = {item['code']: item for item in response.data}
    assert catalog['view_purchase']['module'] == 'purchase'
    assert catalog['view_purchase']['module_label'] == '采购入库'
    assert catalog['view_assignment']['module'] == 'assignment'
    assert catalog['view_assignment']['module_label'] == '领用出库'
    assert catalog['edit_purchase']['prerequisites'] == ['view_purchase', 'view_categories']
    for code in ('edit_assignment', 'edit_transfer', 'edit_recovery'):
        assert 'view_asset_ledger' in catalog[code]['prerequisites']
        assert catalog[code]['conditional_prerequisites']['选择实例管理品目'] == ['view_instances']
    assert catalog['view_reports']['module'] == 'workbench'
    assert catalog['edit_inventory']['label'] == '编辑盘点'
    assert '盘点报告' in catalog['view_inventory']['description']
    assert not {
        'view_return', 'create_return', 'edit_return', 'delete_return_draft',
        'submit_return', 'approve_return', 'withdraw_return',
    } & catalog.keys()
    assert '逐行明细' in catalog['view_reports']['description']
    assert '查看实例档案' in catalog['print_instance_label']['description']
    assert '查看品目' in catalog['edit_categories']['description']
    assert '查看部门字典' in catalog['edit_departments']['description']
    assert '查看供应商字典' in catalog['edit_suppliers']['description']
    assert '查看供应商字典' in catalog['manage_reconciliation']['description']
    assert catalog['manage_reconciliation']['prerequisites'] == [
        'view_reconciliation', 'view_suppliers',
    ]
    assert 'edit_categories' not in catalog['view_categories']['prerequisites']
    assert not {'create_categories', 'delete_categories', 'import_categories'} & catalog.keys()
    assert not {'create_users', 'delete_users', 'create_organizations'} & catalog.keys()
    assert not {'create_purchase', 'submit_purchase', 'withdraw_purchase', 'import_purchase'} & catalog.keys()
    assert '审批本人创建' in catalog['approve_purchase']['description']
    assert 'dispose_assets' not in catalog
    assert '重新入库或直接处置' in catalog['approve_recovery']['description']


@pytest.mark.django_db
def test_my_permissions_returns_authoritative_page_access_directory(branch):
    employee = _employee('13920000021', '页面目录员工', branch=branch)
    OperationGrant.objects.create(user=employee, code='view_recovery_ledger')

    response = _client_for(employee).get('/api/permissions/me')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['page_operations'] == PAGE_ACCESS_OPERATIONS
    assert 'view_recovery_ledger' in response.data['page_operations']['recovery_ledger']
    assert 'view_recovery_ledger' not in response.data['page_operations']['recovery']
    assert 'return' not in response.data['page_operations']
    assert 'approve_return' not in response.data['page_operations']['mobile_approvals']
    assert response.data['page_operations']['inventory'] == ['view_inventory']
    assert 'edit_instances' in response.data['page_operations']['instances']
    assert response.data['page_operations']['categories'] == ['view_categories']
    assert response.data['page_operations']['departments'] == ['view_departments']
    assert response.data['page_operations']['suppliers'] == ['view_suppliers']
    assert set(code for codes in PAGE_ACCESS_OPERATIONS.values() for code in codes) <= {
        item['code'] for item in OPERATION_CATALOG
    }


@pytest.mark.django_db
def test_authorization_save_replaces_grants_and_scope_atomically_with_audit(
    admin_user, branch, second_branch,
):
    employee = _employee('13920000001', '授权员工', branch=branch)
    OperationGrant.objects.create(user=employee, code='view_categories')
    ManagementScope.objects.create(user=employee, branch=branch)
    client = _client_for(admin_user)

    response = client.put(
        f'/api/permissions/users/{employee.id}/authorization',
        {
            'operations': ['view_categories', 'edit_categories'],
            'scope': {
                'mode': 'custom',
                'nodes': [{'type': 'branch', 'id': str(second_branch.id)}],
            },
            'reason': '跨分公司资产管理需要',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    assert set(OperationGrant.objects.filter(user=employee).values_list('code', flat=True)) == {
        'view_categories', 'edit_categories',
    }
    assert list(ManagementScope.objects.filter(user=employee).values_list('branch_id', flat=True)) == [
        second_branch.id,
    ]
    log = AuditLog.objects.filter(
        resource_type='user_authorization', resource_id=employee.id,
    ).order_by('-created_at').first()
    assert log.user_id == admin_user.id
    assert log.before_data['operations'] == ['view_categories']
    assert log.before_data['scope']['nodes'][0]['id'] == str(branch.id)
    assert log.after_data['operations'] == ['edit_categories', 'view_categories']
    assert log.after_data['scope']['nodes'][0]['id'] == str(second_branch.id)
    assert '跨分公司资产管理需要' in log.description


@pytest.mark.django_db
def test_authorization_change_allows_blank_audit_reason(admin_user, branch):
    employee = _employee('13920000007', '未填写原因的授权员工', branch=branch)

    response = _client_for(admin_user).put(
        f'/api/permissions/users/{employee.id}/authorization',
        {
            'operations': ['view_instances'],
            'scope': {'mode': 'default', 'nodes': []},
        },
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    log = AuditLog.objects.get(
        resource_type='user_authorization', resource_id=employee.id,
    )
    assert log.description == '账号权限与数据范围已更新'
    assert log.before_data['operations'] == []
    assert log.after_data['operations'] == ['view_instances']


@pytest.mark.django_db
def test_saving_unchanged_authorization_does_not_write_change_audit(admin_user, branch):
    employee = _employee('13920000020', '授权未变化员工', branch=branch)
    OperationGrant.objects.create(user=employee, code='view_instances')
    ManagementScope.objects.create(user=employee, branch=branch)

    response = _client_for(admin_user).put(
        f'/api/permissions/users/{employee.id}/authorization',
        {
            'operations': ['view_instances'],
            'scope': {
                'mode': 'custom',
                'nodes': [{'type': 'branch', 'id': str(branch.id)}],
            },
        },
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    assert not AuditLog.objects.filter(
        resource_type='user_authorization', resource_id=employee.id,
    ).exists()


@pytest.mark.django_db
def test_invalid_authorization_does_not_partially_change_existing_data(admin_user, branch):
    employee = _employee('13920000002', '不完整保存员工', branch=branch)
    grant = OperationGrant.objects.create(user=employee, code='view_categories')
    scope = ManagementScope.objects.create(user=employee, branch=branch)
    client = _client_for(admin_user)

    response = client.put(
        f'/api/permissions/users/{employee.id}/authorization',
        {
            'operations': ['edit_categories', 'not_a_real_permission'],
            'scope': {'mode': 'all', 'nodes': []},
        },
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert OperationGrant.objects.filter(pk=grant.pk).exists()
    assert ManagementScope.objects.filter(pk=scope.pk).exists()
    assert not AuditLog.objects.filter(resource_type='user_authorization').exists()


@pytest.mark.django_db
def test_authorization_api_rejects_missing_declared_view_prerequisite(admin_user, branch):
    employee = _employee('13920000032', '缺少前置员工', branch=branch)
    existing_grant = OperationGrant.objects.create(user=employee, code='view_categories')
    existing_scope = ManagementScope.objects.create(user=employee, branch=branch)

    response = _client_for(admin_user).put(
        f'/api/permissions/users/{employee.id}/authorization',
        {
            'operations': ['edit_categories'],
            'scope': {'mode': 'all', 'nodes': []},
        },
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert '查看品目' in response.data['detail']
    assert OperationGrant.objects.filter(pk=existing_grant.pk).exists()
    assert ManagementScope.objects.filter(pk=existing_scope.pk).exists()


@pytest.mark.django_db
def test_user_can_requires_declared_view_prerequisite(branch):
    employee = _employee('13920000033', '运行时前置员工', branch=branch)
    OperationGrant.objects.create(user=employee, code='edit_categories')

    assert employee.can('edit_categories') is False

    OperationGrant.objects.create(user=employee, code='view_categories')

    assert employee.can('edit_categories') is True
    assert employee.can('create_categories') is False


@pytest.mark.django_db
@pytest.mark.parametrize('legacy_code', ['manage_assets', 'dispose_assets'])
def test_authorization_api_preserves_legacy_grants_until_explicitly_removed(
    admin_user, branch, legacy_code,
):
    employee = _employee('13920000003', '旧权限员工', branch=branch)
    OperationGrant.objects.create(user=employee, code=legacy_code)
    client = _client_for(admin_user)

    current = client.get(f'/api/permissions/users/{employee.id}/authorization')
    assert current.status_code == status.HTTP_200_OK
    assert current.data['legacy_operations'] == [legacy_code]
    if legacy_code == 'dispose_assets':
        assert current.data['legacy_operation_details'] == [{
            'code': 'dispose_assets',
            'label': '处置回收物资（旧权限，需人工核对）',
        }]

    saved = client.put(
        f'/api/permissions/users/{employee.id}/authorization',
        {'operations': [], 'scope': {'mode': 'default', 'nodes': []}},
        format='json',
    )
    assert saved.status_code == status.HTTP_200_OK
    assert saved.data['legacy_operations'] == [legacy_code]
    assert OperationGrant.objects.filter(user=employee, code=legacy_code).exists()

    removed = client.put(
        f'/api/permissions/users/{employee.id}/authorization',
        {
            'operations': ['view_instances'],
            'scope': {'mode': 'default', 'nodes': []},
            'remove_legacy_operations': [legacy_code],
        },
        format='json',
    )
    assert removed.status_code == status.HTTP_200_OK
    assert removed.data['legacy_operations'] == []
    assert set(OperationGrant.objects.filter(user=employee).values_list('code', flat=True)) == {
        'view_instances',
    }
    log = AuditLog.objects.filter(
        resource_type='user_authorization', resource_id=employee.id,
    ).order_by('-created_at').first()
    assert log.before_data['operations'] == [legacy_code]
    assert log.after_data['legacy_operations'] == []
    assert log.after_data['operations'] == ['view_instances']

    admin_update = client.put(
        f'/api/permissions/users/{admin_user.id}/authorization',
        {'operations': [], 'scope': {'mode': 'default', 'nodes': []}},
        format='json',
    )
    assert admin_update.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_permission_matrix_and_audit_log_require_separate_grants(branch):
    employee = _employee('13920000004', '矩阵查看者', branch=branch)
    client = _client_for(employee)

    assert client.get('/api/permissions/effective').status_code == status.HTTP_403_FORBIDDEN
    assert client.get('/api/permissions/matrix-organizations').status_code == status.HTTP_403_FORBIDDEN
    assert client.get('/api/audit/').status_code == status.HTTP_403_FORBIDDEN

    OperationGrant.objects.create(user=employee, code='view_permission_matrix')
    matrix = client.get('/api/permissions/effective')
    assert matrix.status_code == status.HTTP_200_OK
    assert any(row['user'] == str(employee.id) for row in matrix.data)
    organizations = client.get('/api/permissions/matrix-organizations')
    assert organizations.status_code == status.HTTP_200_OK
    assert {'id': str(branch.team.region_id), 'name': branch.team.region.name} in organizations.data['regions']
    assert {
        'id': str(branch.id), 'name': branch.name, 'region': str(branch.team.region_id),
    } in organizations.data['branches']
    assert client.get('/api/audit/').status_code == status.HTTP_403_FORBIDDEN

    OperationGrant.objects.create(user=employee, code='view_audit_logs')
    assert client.get('/api/audit/').status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_branch_change_preserves_grants_and_clears_custom_scope(
    admin_user, branch, second_branch,
):
    employee = _employee('13920000005', '待调岗员工', branch=branch)
    OperationGrant.objects.create(user=employee, code='view_categories')
    ManagementScope.objects.create(user=employee, branch=second_branch)
    client = _client_for(admin_user)

    response = client.patch(
        f'/api/users/{employee.id}',
        {'branch': str(second_branch.id)},
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    assert list(employee.operation_grants.values_list('code', flat=True)) == ['view_categories']
    assert not ManagementScope.objects.filter(user=employee).exists()
    reset_log = AuditLog.objects.get(
        resource_type='user_authorization', resource_id=employee.id,
    )
    assert reset_log.user_id == admin_user.id
    assert reset_log.before_data['employee'] == {
        'role': 'manager', 'role_label': 'manager',
        'branch_id': str(branch.id), 'branch_name': branch.name,
    }
    assert reset_log.before_data['operations'] == ['view_categories']
    assert reset_log.before_data['scopes'][0]['branch'] == str(second_branch.id)
    assert reset_log.after_data == {
        'employee': {
            'role': 'manager', 'role_label': 'manager',
            'branch_id': str(second_branch.id), 'branch_name': second_branch.name,
        },
        'operations': ['view_categories'], 'scopes': [],
    }


@pytest.mark.django_db
def test_clearing_employee_branch_preserves_grants_and_clears_scope(admin_user, branch):
    employee = _employee('13920000006', '解绑分公司员工', branch=branch)
    OperationGrant.objects.create(user=employee, code='view_categories')
    ManagementScope.objects.create(user=employee, branch=branch)

    response = _client_for(admin_user).patch(
        f'/api/users/{employee.id}', {'branch': None}, format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    employee.refresh_from_db()
    assert employee.branch_id is None
    assert list(employee.operation_grants.values_list('code', flat=True)) == ['view_categories']
    assert not ManagementScope.objects.filter(user=employee).exists()
    reset_log = AuditLog.objects.get(
        resource_type='user_authorization', resource_id=employee.id,
    )
    assert reset_log.before_data['operations'] == ['view_categories']
    assert reset_log.before_data['scopes'][0]['branch'] == str(branch.id)
    assert reset_log.before_data['employee']['branch_id'] == str(branch.id)
    assert reset_log.before_data['employee']['branch_name'] == branch.name
    assert reset_log.after_data['employee']['branch_id'] is None
    assert reset_log.after_data['employee']['branch_name'] is None
    assert reset_log.after_data['operations'] == ['view_categories']
    assert reset_log.after_data['scopes'] == []


@pytest.mark.django_db
def test_role_change_resets_employee_grants_scope_and_audits(admin_user, branch):
    from apps.permissions.position_baselines import get_role_baseline

    employee = _employee('13920000008', '调岗员工', branch=branch)
    OperationGrant.objects.create(user=employee, code='view_instances')
    ManagementScope.objects.create(user=employee, is_all_data=True)

    response = _client_for(admin_user).patch(
        f'/api/users/{employee.id}', {'role': 'leader'}, format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    employee.refresh_from_db()
    assert employee.role == 'leader'
    expected_grants = sorted(get_role_baseline('leader'))
    assert sorted(employee.operation_grants.values_list('code', flat=True)) == expected_grants
    assert not ManagementScope.objects.filter(user=employee).exists()
    reset_log = AuditLog.objects.get(
        resource_type='user_authorization', resource_id=employee.id,
    )
    assert reset_log.before_data['operations'] == ['view_instances']
    assert reset_log.before_data['scopes'] == [{
        'all': True, 'region': None, 'branch': None, 'team': None,
    }]
    assert reset_log.before_data['employee']['role'] == 'manager'
    assert reset_log.before_data['employee']['branch_id'] == str(branch.id)
    assert reset_log.after_data['employee'] == {
        'role': 'leader', 'role_label': 'leader',
        'branch_id': str(branch.id), 'branch_name': branch.name,
    }
    assert reset_log.after_data['operations'] == expected_grants
    assert reset_log.after_data['scopes'] == []


@pytest.mark.django_db
def test_employee_account_actions_use_edit_grant_and_view_prerequisite(branch):
    employee = _employee('13920000009', '账号操作员', branch=branch)
    OperationGrant.objects.create(user=employee, code='edit_users')
    client = _client_for(employee)

    payload = {
        'phone': '13920000019', 'name': '新员工', 'role': 'leader',
        'status': 'active', 'password': 'test123456', 'branch': str(branch.id),
    }
    assert client.post('/api/users/', payload, format='json').status_code == status.HTTP_403_FORBIDDEN
    OperationGrant.objects.create(user=employee, code='view_users')
    created = client.post('/api/users/', payload, format='json')
    assert created.status_code == status.HTTP_201_CREATED
    user_id = created.data['id']
    assert client.patch(f'/api/users/{user_id}', {'name': '改名'}, format='json').status_code == status.HTTP_200_OK
    assert client.delete(f'/api/users/{user_id}').status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_organization_actions_use_edit_grant_and_view_prerequisite(branch):
    from apps.organizations.models import Region
    from apps.permissions.models import ManagementScope

    employee = _employee('13920000010', '组织操作员', branch=branch)
    ManagementScope.objects.create(user=employee, is_all_data=True)
    OperationGrant.objects.create(user=employee, code='edit_organizations')
    client = _client_for(employee)

    payload = {
        'name': '新建区域', 'code': 'NEW-REGION', 'status': 'active',
    }
    assert client.post('/api/regions/', payload, format='json').status_code == status.HTTP_403_FORBIDDEN
    OperationGrant.objects.create(user=employee, code='view_organizations')
    created = client.post('/api/regions/', payload, format='json')
    assert created.status_code == status.HTTP_201_CREATED
    region_id = created.data['id']
    assert client.delete(f'/api/regions/{region_id}').status_code == status.HTTP_403_FORBIDDEN
    assert client.patch(f'/api/regions/{region_id}', {'name': '修改区域'}, format='json').status_code == status.HTTP_200_OK
    assert client.delete(f'/api/regions/{region_id}').status_code == status.HTTP_403_FORBIDDEN

    OperationGrant.objects.create(user=employee, code='delete_organizations')
    assert client.delete(f'/api/regions/{region_id}').status_code == status.HTTP_204_NO_CONTENT
    assert not Region.objects.filter(pk=region_id).exists()


@pytest.mark.django_db
def test_department_and_supplier_edits_and_deletes_require_view(branch):
    from apps.organizations.models import Department
    from apps.suppliers.models import Supplier

    employee = _employee('13920000011', '字典操作员', branch=branch)
    client = _client_for(employee)
    OperationGrant.objects.create(user=employee, code='create_departments')
    created_department = client.post('/api/departments/', {'name': '新增测试部门'}, format='json')
    assert created_department.status_code == status.HTTP_403_FORBIDDEN
    OperationGrant.objects.create(user=employee, code='delete_departments')
    OperationGrant.objects.create(user=employee, code='edit_departments')
    assert client.post('/api/departments/', {'name': '缺查看权限的部门'}, format='json').status_code == status.HTTP_403_FORBIDDEN
    OperationGrant.objects.create(user=employee, code='view_departments')
    created_department = client.post('/api/departments/', {'name': '新增测试部门'}, format='json')
    assert created_department.status_code == status.HTTP_201_CREATED
    department_id = created_department.data['id']
    assert client.patch(f'/api/departments/{department_id}', {'name': '修改测试部门'}, format='json').status_code == status.HTTP_200_OK

    employee.operation_grants.all().delete()
    employee.operation_grants.create(code='create_departments')
    employee.operation_grants.create(code='delete_departments')
    assert client.post('/api/departments/', {'name': '旧权限不得新增'}, format='json').status_code == status.HTTP_403_FORBIDDEN
    assert client.delete(f'/api/departments/{department_id}').status_code == status.HTTP_403_FORBIDDEN
    employee.operation_grants.create(code='view_departments')
    employee.operation_grants.create(code='edit_departments')
    assert client.delete(f'/api/departments/{department_id}').status_code == status.HTTP_204_NO_CONTENT
    assert not Department.objects.filter(pk=department_id).exists()

    OperationGrant.objects.create(user=employee, code='create_suppliers')
    created_supplier = client.post('/api/suppliers/', {'name': '新增测试供应商'}, format='json')
    assert created_supplier.status_code == status.HTTP_403_FORBIDDEN
    OperationGrant.objects.create(user=employee, code='delete_suppliers')
    OperationGrant.objects.create(user=employee, code='edit_suppliers')
    assert client.post('/api/suppliers/', {'name': '缺查看权限的供应商'}, format='json').status_code == status.HTTP_403_FORBIDDEN
    OperationGrant.objects.create(user=employee, code='view_suppliers')
    created_supplier = client.post('/api/suppliers/', {'name': '新增测试供应商'}, format='json')
    assert created_supplier.status_code == status.HTTP_201_CREATED
    supplier_id = created_supplier.data['id']
    assert client.patch(f'/api/suppliers/{supplier_id}', {'name': '修改测试供应商'}, format='json').status_code == status.HTTP_200_OK

    employee.operation_grants.all().delete()
    employee.operation_grants.create(code='create_suppliers')
    employee.operation_grants.create(code='delete_suppliers')
    assert client.post('/api/suppliers/', {'name': '旧权限不得新增'}, format='json').status_code == status.HTTP_403_FORBIDDEN
    assert client.delete(f'/api/suppliers/{supplier_id}').status_code == status.HTTP_403_FORBIDDEN
    employee.operation_grants.create(code='view_suppliers')
    employee.operation_grants.create(code='edit_suppliers')
    assert client.delete(f'/api/suppliers/{supplier_id}').status_code == status.HTTP_204_NO_CONTENT
    assert not Supplier.objects.filter(pk=supplier_id).exists()


@pytest.mark.django_db
def test_organization_operations_respect_account_scope(
    branch, second_branch, region, second_region,
):
    employee = _employee('13920000012', '分公司组织操作员', branch=branch)
    for code in ('view_organizations', 'create_organizations', 'edit_organizations', 'delete_organizations'):
        OperationGrant.objects.create(user=employee, code=code)
    client = _client_for(employee)

    regions = client.get('/api/regions/')
    assert regions.status_code == status.HTTP_200_OK
    assert [row['id'] for row in regions.data] == [str(region.id)]

    branches = client.get('/api/branches/')
    assert branches.status_code == status.HTTP_200_OK
    assert {row['id'] for row in branches.data} == {str(branch.id)}

    assert client.patch(
        f'/api/branches/{branch.id}', {'name': '本范围内名称'}, format='json',
    ).status_code == status.HTTP_200_OK
    assert client.patch(
        f'/api/branches/{second_branch.id}', {'name': '越权名称'}, format='json',
    ).status_code == status.HTTP_404_NOT_FOUND
    assert client.patch(
        f'/api/regions/{region.id}', {'name': '越权上级修改'}, format='json',
    ).status_code == status.HTTP_404_NOT_FOUND
    assert client.post('/api/regions/', {
        'name': '越权新增区域', 'code': 'OUTSIDE', 'status': 'active',
    }, format='json').status_code == status.HTTP_403_FORBIDDEN
    assert client.post('/api/teams/', {
        'name': '越权新增行政组', 'region': str(region.id), 'status': 'active',
    }, format='json').status_code == status.HTTP_403_FORBIDDEN
    assert client.post('/api/branches/', {
        'name': '越权新增分公司', 'code': 'OUT001', 'team': str(second_branch.team_id),
    }, format='json').status_code == status.HTTP_403_FORBIDDEN


def test_authorization_models_are_read_only_in_django_admin():
    from django.contrib.admin.sites import site
    from apps.permissions.models import ManagementScope, OperationGrant

    for model in (ManagementScope, OperationGrant):
        model_admin = site._registry[model]
        assert not model_admin.has_add_permission(None)
        assert not model_admin.has_change_permission(None)
        assert not model_admin.has_delete_permission(None)
