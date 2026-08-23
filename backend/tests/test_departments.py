"""部门字典契约测试（department-dictionary 能力）。"""
import pytest
from conftest import _client_for
from rest_framework import status


@pytest.mark.django_db
class TestDepartmentModel:
    def test_same_branch_duplicate_rejected(self, branch):
        from apps.organizations.models import Department
        from django.db import IntegrityError
        Department.objects.create(branch=branch, name='行政部')
        with pytest.raises(IntegrityError):
            Department.objects.create(branch=branch, name='行政部')

    def test_same_name_across_branches_allowed(self, branch, second_branch):
        from apps.organizations.models import Department
        Department.objects.create(branch=branch, name='行政部')
        Department.objects.create(branch=second_branch, name='行政部')
        assert Department.objects.filter(name='行政部').count() == 2


@pytest.mark.django_db
class TestDepartmentAPI:
    def _auth(self, user):
        return _client_for(user)

    def test_create_and_list(self, admin_user, branch):
        client = self._auth(admin_user)
        resp = client.post('/api/departments/', {'branch': str(branch.id), 'name': '财务部'}, format='json')
        assert resp.status_code == 201
        assert resp.data['branch_name'] == branch.name
        resp = client.get('/api/departments/')
        assert resp.status_code == 200

    def test_duplicate_returns_400_with_hint(self, admin_user, branch):
        from apps.organizations.models import Department
        Department.objects.create(branch=branch, name='人事部')
        client = self._auth(admin_user)
        resp = client.post('/api/departments/', {'branch': str(branch.id), 'name': '人事部'}, format='json')
        assert resp.status_code == 400
        assert '唯一' in str(resp.data) or '已存在' in str(resp.data)

    def test_create_requires_permission(self, staff_user, branch):
        client = self._auth(staff_user)
        resp = client.post('/api/departments/', {'branch': str(branch.id), 'name': '仓库'}, format='json')
        assert resp.status_code == 403

    def test_options_filters_by_branch(self, staff_user, branch, second_branch):
        from apps.organizations.models import Department
        Department.objects.create(branch=branch, name='行政部')
        Department.objects.create(branch=second_branch, name='市场部')
        client = self._auth(staff_user)
        resp = client.get('/api/departments/options', {'branch': branch.name})
        assert resp.status_code == 200
        names = [d['name'] for d in resp.data]
        assert names == ['行政部']

    def test_options_scoped_to_own_branch(self, staff_user, branch, second_branch):
        from apps.organizations.models import Department
        Department.objects.create(branch=branch, name='行政部')
        Department.objects.create(branch=second_branch, name='市场部')
        client = self._auth(staff_user)
        resp = client.get('/api/departments/options')
        names = [d['name'] for d in resp.data]
        assert '行政部' in names
        assert '市场部' not in names
