"""供应商字典契约测试（supplier-dictionary 能力）。"""
import pytest
from conftest import _client_for
from rest_framework import status


@pytest.mark.django_db
class TestSupplierDictionary:
    def _auth(self, user):
        return _client_for(user)

    def test_admin_crud(self, admin_user):
        from apps.suppliers.models import Supplier
        client = self._auth(admin_user)
        resp = client.post('/api/suppliers/', {'name': '得力办公', '联系人': '王经理', '电话': '13800000000'}, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        sid = resp.data['id']

        resp = client.get('/api/suppliers/')
        assert resp.status_code == status.HTTP_200_OK
        assert any(s['name'] == '得力办公' for s in resp.data['results'])

        resp = client.patch(f'/api/suppliers/{sid}', {'电话': '13900000000'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert Supplier.objects.get(pk=sid).电话 == '13900000000'

        resp = client.delete(f'/api/suppliers/{sid}')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_duplicate_name_rejected(self, admin_user):
        from apps.suppliers.models import Supplier
        Supplier.objects.create(name='得力办公')
        resp = self._auth(admin_user).post('/api/suppliers/', {'name': '得力办公'}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '已存在' in str(resp.data)

    def test_non_admin_can_read_but_not_write(self, staff_user):
        from apps.suppliers.models import Supplier
        Supplier.objects.create(name='得力办公')
        client = self._auth(staff_user)
        resp = client.get('/api/suppliers/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['results'][0]['name'] == '得力办公'
        resp = client.post('/api/suppliers/', {'name': '新供应商'}, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN
