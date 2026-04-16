"""Permission tests: role-based access control and data scoping."""
import pytest
from rest_framework import status


@pytest.mark.django_db
class TestRoleAccess:
    def test_unauthenticated_gets_401(self, api_client):
        resp = api_client.get('/api/users')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_staff_cannot_create_users(self, staff_client):
        resp = staff_client.post('/api/users', {
            'phone': '13900000010',
            'name': 'New User',
            'password': 'test123456',
            'role': 'staff',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_create_users(self, authenticated_client):
        resp = authenticated_client.post('/api/users', {
            'phone': '13900000010',
            'name': 'New User',
            'password': 'test123456',
            'role': 'staff',
        })
        assert resp.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestDataScope:
    def test_staff_sees_own_branch_assets(self, staff_client, staff_user):
        resp = staff_client.get('/api/assets')
        assert resp.status_code == status.HTTP_200_OK
        # Staff should only see assets from their own branch
        if resp.data.get('results'):
            for asset in resp.data['results']:
                assert asset.get('分公司') == staff_user.branch.name

    def test_admin_sees_all_assets(self, authenticated_client):
        resp = authenticated_client.get('/api/assets')
        assert resp.status_code == status.HTTP_200_OK
