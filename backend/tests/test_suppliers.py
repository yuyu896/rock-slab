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
        from apps.permissions.models import OperationGrant
        Supplier.objects.create(name='得力办公')
        OperationGrant.objects.get_or_create(user=staff_user, code='view_suppliers')
        client = self._auth(staff_user)
        resp = client.get('/api/suppliers/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['results'][0]['name'] == '得力办公'
        resp = client.post('/api/suppliers/', {'name': '新供应商'}, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_edit_permission_controls_create_edit_delete_and_requires_view(self, staff_user):
        from apps.permissions.models import OperationGrant
        from apps.suppliers.models import Supplier

        supplier = Supplier.objects.create(name='权限测试供应商')
        OperationGrant.objects.create(user=staff_user, code='edit_suppliers')
        client = self._auth(staff_user)

        assert client.post('/api/suppliers/', {'name': '新供应商'}, format='json').status_code == 403
        assert client.patch(
            f'/api/suppliers/{supplier.id}', {'name': '改名供应商'}, format='json',
        ).status_code == 403
        assert client.delete(f'/api/suppliers/{supplier.id}').status_code == 403

        OperationGrant.objects.create(user=staff_user, code='view_suppliers')
        created = client.post('/api/suppliers/', {'name': '新供应商'}, format='json')
        assert created.status_code == status.HTTP_201_CREATED
        assert client.patch(
            f'/api/suppliers/{supplier.id}', {'name': '改名供应商'}, format='json',
        ).status_code == status.HTTP_200_OK
        assert client.delete(f'/api/suppliers/{supplier.id}').status_code == status.HTTP_204_NO_CONTENT

    def test_instance_editor_needs_supplier_view_for_name_options(self, staff_user):
        from apps.suppliers.models import Supplier
        from apps.permissions.models import OperationGrant

        supplier = Supplier.objects.create(name='编辑选项供应商', 联系人='不应返回', 电话='13800000000')
        OperationGrant.objects.create(user=staff_user, code='edit_instances')
        client = self._auth(staff_user)

        response = client.get('/api/suppliers/instance-options')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        OperationGrant.objects.create(user=staff_user, code='view_suppliers')
        OperationGrant.objects.create(user=staff_user, code='view_instances')
        response = client.get('/api/suppliers/instance-options')
        assert response.status_code == status.HTTP_200_OK
        assert {str(row['id']) for row in response.data} == {str(supplier.pk)}
        assert response.data[0]['name'] == supplier.name
        assert set(response.data[0]) == {'id', 'name'}
        assert client.get('/api/suppliers/').status_code == status.HTTP_200_OK
