import pytest
from rest_framework import status

from conftest import _client_for


def _grant(user, code):
    from apps.permissions.models import OperationGrant

    OperationGrant.objects.get_or_create(user=user, code=code)


@pytest.mark.django_db
class TestUserWriteOptions:
    def test_edit_only_gets_scoped_edit_targets_without_directory_access(
        self, db, branch, second_branch,
    ):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        editor = User.objects.create_user(
            phone='13900000101', name='员工编辑员', password='test123456',
            role='manager', status='active', branch=branch,
        )
        target = User.objects.create_user(
            phone='13900000102', name='范围内员工', password='test123456',
            role='leader', status='active', branch=branch,
        )
        outside = User.objects.create_user(
            phone='13900000103', name='范围外员工', password='test123456',
            role='leader', status='active', branch=second_branch,
        )
        _grant(editor, 'view_users')
        _grant(editor, 'edit_users')
        client = _client_for(editor)

        response = client.get('/api/users/', {'scope': 'write'})

        assert response.status_code == status.HTTP_200_OK
        rows = {row['id']: row for row in response.data}
        assert str(target.id) in rows
        assert str(outside.id) not in rows
        assert set(rows[str(target.id)]) == {
            'id', 'name', 'phone', 'role', 'status', 'branch', 'branch_name',
        }
        assert client.get('/api/users/').status_code == status.HTTP_200_OK

    def test_delete_only_grant_cannot_get_employee_targets(self, db, branch):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        deleter = User.objects.create_user(
            phone='13900000104', name='员工删除员', password='test123456',
            role='manager', status='active', branch=branch,
        )
        target = User.objects.create_user(
            phone='13900000105', name='待删除员工', password='test123456',
            role='leader', status='active', branch=branch,
        )
        _grant(deleter, 'delete_users')

        response = _client_for(deleter).get('/api/users/', {'scope': 'write'})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_only_does_not_open_user_target_directory(self, db, branch):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            phone='13900000106', name='仅创建员工', password='test123456',
            role='manager', status='active', branch=branch,
        )
        _grant(user, 'create_users')

        response = _client_for(user).get('/api/users/', {'scope': 'write'})

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestOrganizationTreeWriteOptions:
    def test_legacy_create_permission_is_not_organization_edit(self, db, region):
        from django.contrib.auth import get_user_model

        editor = get_user_model().objects.create_user(
            phone='13900000112', name='旧组织新增权限', password='test123456',
            role='manager', status='active',
        )
        _grant(editor, 'view_organizations')
        _grant(editor, 'create_organizations')
        from apps.permissions.models import ManagementScope
        ManagementScope.objects.create(user=editor, is_all_data=True)

        response = _client_for(editor).post('/api/regions/', {
            'name': '不应创建', 'code': 'NO-CREATE', 'status': 'active',
        }, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_edit_permission_covers_organization_create_and_update(self, db, region):
        from django.contrib.auth import get_user_model
        from apps.permissions.models import ManagementScope

        editor = get_user_model().objects.create_user(
            phone='13900000113', name='组织编辑权限', password='test123456',
            role='manager', status='active',
        )
        ManagementScope.objects.create(user=editor, is_all_data=True)
        _grant(editor, 'view_organizations')
        _grant(editor, 'edit_organizations')
        client = _client_for(editor)

        created = client.post('/api/regions/', {
            'name': '编辑权限新增区域', 'code': 'EDIT-REGION', 'status': 'active',
        }, format='json')
        assert created.status_code == status.HTTP_201_CREATED
        updated = client.patch(
            f"/api/regions/{region.id}", {'name': '编辑权限修改区域'}, format='json',
        )
        assert updated.status_code == status.HTTP_200_OK

    def test_company_name_patch_requires_full_scope(self, db, branch):
        from django.contrib.auth import get_user_model

        editor = get_user_model().objects.create_user(
            phone='13900000114', name='局部范围组织编辑员', password='test123456',
            role='manager', status='active', branch=branch,
        )
        _grant(editor, 'view_organizations')
        _grant(editor, 'edit_organizations')

        response = _client_for(editor).patch('/api/company/', {'name': '越权名称'})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_normal_directory_marks_context_only_parents_not_writable(self, db, branch):
        from django.contrib.auth import get_user_model

        editor = get_user_model().objects.create_user(
            phone='13900000111', name='组织目录编辑员', password='test123456',
            role='manager', status='active', branch=branch,
        )
        _grant(editor, 'view_organizations')
        _grant(editor, 'edit_organizations')
        client = _client_for(editor)

        regions = client.get('/api/regions/')
        teams = client.get('/api/teams/')

        assert regions.status_code == teams.status_code == status.HTTP_200_OK
        assert regions.data[0]['can_manage'] is False
        assert teams.data[0]['can_manage'] is False

    def test_editor_gets_only_scoped_tree_path_and_company_name(
        self, db, branch, second_branch,
    ):
        from django.contrib.auth import get_user_model

        editor = get_user_model().objects.create_user(
            phone='13900000107', name='组织编辑员', password='test123456',
            role='manager', status='active', branch=branch,
        )
        _grant(editor, 'view_organizations')
        _grant(editor, 'edit_organizations')
        client = _client_for(editor)

        regions = client.get('/api/regions/', {'scope': 'tree'})
        teams = client.get('/api/teams/', {'scope': 'tree'})
        branches = client.get('/api/branches/', {'scope': 'tree'})
        company = client.get('/api/company/', {'scope': 'tree'})

        assert regions.status_code == teams.status_code == branches.status_code == 200
        assert [row['id'] for row in regions.data] == [str(branch.team.region_id)]
        assert [row['id'] for row in teams.data] == [str(branch.team_id)]
        assert [row['id'] for row in branches.data] == [str(branch.id)]
        assert second_branch.id not in [row['id'] for row in branches.data]
        assert set(regions.data[0]) == {'id', 'name', 'code', 'status', 'can_manage'}
        assert regions.data[0]['can_manage'] is False
        assert set(teams.data[0]) == {'id', 'name', 'region', 'status', 'can_manage'}
        assert teams.data[0]['can_manage'] is False
        assert set(branches.data[0]) == {
            'id', 'name', 'code', 'team', 'team_name', 'region', 'region_name',
            'address', 'phone', 'status',
        }
        assert set(company.data) == {'id', 'name', 'can_create_region'}
        assert company.data['can_create_region'] is False
        assert client.get('/api/regions/').status_code == status.HTTP_200_OK
        assert client.get('/api/company/').status_code == status.HTTP_200_OK

    def test_delete_only_tree_does_not_include_edit_fields(self, db, branch):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            phone='13900000108', name='组织删除员', password='test123456',
            role='manager', status='active', branch=branch,
        )
        _grant(user, 'view_organizations')
        _grant(user, 'delete_organizations')

        response = _client_for(user).get('/api/branches/', {'scope': 'tree'})

        assert response.status_code == status.HTTP_200_OK
        assert set(response.data[0]) == {
            'id', 'name', 'team', 'team_name', 'region', 'region_name',
        }

    def test_unchanged_parent_is_allowed_for_scoped_updates(
        self, db, branch, second_branch, team, region,
    ):
        from django.contrib.auth import get_user_model
        from apps.permissions.models import ManagementScope

        User = get_user_model()
        team_editor = User.objects.create_user(
            phone='13900000109', name='组织范围编辑员', password='test123456',
            role='manager', status='active',
        )
        _grant(team_editor, 'view_organizations')
        _grant(team_editor, 'edit_organizations')
        ManagementScope.objects.create(user=team_editor, team=team)

        team_response = _client_for(team_editor).patch(
            f'/api/teams/{team.id}', {'name': '行政组改名', 'region': str(region.id)},
            format='json',
        )

        branch_editor = User.objects.create_user(
            phone='13900000110', name='分公司范围编辑员', password='test123456',
            role='manager', status='active', branch=branch,
        )
        _grant(branch_editor, 'view_organizations')
        _grant(branch_editor, 'edit_organizations')
        branch_response = _client_for(branch_editor).patch(
            f'/api/branches/{branch.id}', {'name': '分公司改名', 'team': str(team.id)},
            format='json',
        )

        assert team_response.status_code == status.HTTP_200_OK
        assert branch_response.status_code == status.HTTP_200_OK

        changed_parent = _client_for(branch_editor).patch(
            f'/api/branches/{branch.id}', {'team': str(second_branch.team_id)},
            format='json',
        )
        assert changed_parent.status_code == status.HTTP_403_FORBIDDEN
