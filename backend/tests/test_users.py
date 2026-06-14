"""Tests for UserViewSet: CRUD, role assignment, scope, auto-assignment, avatar."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from conftest import _client_for


def _user_payload(**overrides):
    defaults = dict(
        phone='13811112222',
        name='新建用户',
        role='staff',
        status='active',
        password='123456',
    )
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserCRUD:
    def test_list_users(self, authenticated_client, admin_user, staff_user):
        resp = authenticated_client.get('/api/users/')
        assert resp.status_code == status.HTTP_200_OK
        ids = [str(u['id']) for u in resp.data]
        assert str(admin_user.id) in ids
        assert str(staff_user.id) in ids

    def test_list_users_no_pagination(self, authenticated_client):
        resp = authenticated_client.get('/api/users/')
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)

    def test_create_user_valid(self, authenticated_client, region):
        payload = _user_payload(region=region.id)
        resp = authenticated_client.post('/api/users/', payload)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['phone'] == payload['phone']
        assert resp.data['name'] == payload['name']

    @pytest.mark.xfail(reason='No UniqueValidator on phone field; IntegrityError crashes via audit_log decorator')
    def test_create_user_duplicate_phone(self, authenticated_client, staff_user):
        payload = _user_payload(phone=staff_user.phone)
        resp = authenticated_client.post('/api/users/', payload)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_user_name(self, authenticated_client, staff_user):
        resp = authenticated_client.patch(f'/api/users/{staff_user.id}', {
            'name': '新名字',
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['name'] == '新名字'
        staff_user.refresh_from_db()
        assert staff_user.name == '新名字'

    def test_delete_user(self, authenticated_client, region, branch):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        target = User.objects.create_user(
            phone='13800009999', name='待删除', password='123456',
            role='staff', status='active', region=region, branch=branch,
        )
        resp = authenticated_client.delete(f'/api/users/{target.id}')
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(id=target.id).exists()


# ---------------------------------------------------------------------------
# Role assignment validation (MANAGEABLE_ROLES)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRoleAssignment:
    def test_supervisor_creates_leader(self, supervisor_user, region):
        client = _client_for(supervisor_user)
        payload = _user_payload(role='leader', region=region.id)
        resp = client.post('/api/users/', payload)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['role'] == 'leader'

    def test_supervisor_cannot_create_supervisor(self, supervisor_user, region):
        client = _client_for(supervisor_user)
        payload = _user_payload(role='supervisor', region=region.id)
        resp = client.post('/api/users/', payload)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_leader_cannot_create_user(self, leader_user):
        client = _client_for(leader_user)
        payload = _user_payload()
        resp = client.post('/api/users/', payload)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_creates_admin(self, admin_user):
        client = _client_for(admin_user)
        payload = _user_payload(role='admin')
        resp = client.post('/api/users/', payload)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['role'] == 'admin'

    def test_supervisor_cannot_create_manager(self, supervisor_user, region):
        client = _client_for(supervisor_user)
        payload = _user_payload(role='manager', region=region.id)
        resp = client.post('/api/users/', payload)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Scope validation (_validate_in_scope)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestScopeValidation:
    def test_supervisor_edits_user_in_own_region(self, supervisor_user, staff_user, region):
        # supervisor_user and staff_user are both in `region`
        staff_user.region = region
        staff_user.save(update_fields=['region', 'updated_at'])
        client = _client_for(supervisor_user)
        resp = client.patch(f'/api/users/{staff_user.id}', {'name': '同区域内编辑'})
        assert resp.status_code == status.HTTP_200_OK

    def test_supervisor_edits_user_in_different_region(self, supervisor_user, staff_b):
        # supervisor_user's scope only includes their own region, so staff_b
        # (in second_region) is not in their queryset — get_object() returns 404.
        client = _client_for(supervisor_user)
        resp = client.patch(f'/api/users/{staff_b.id}', {'name': '跨区域编辑'})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_staff_cannot_edit_anyone(self, staff_user, admin_user):
        client = _client_for(staff_user)
        resp = client.patch(f'/api/users/{admin_user.id}', {'name': '无权限编辑'})
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# Auto-assignment
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAutoAssignment:
    def test_supervisor_creates_user_without_region_auto_sets(self, supervisor_user):
        client = _client_for(supervisor_user)
        payload = _user_payload(role='staff')  # no region provided
        resp = client.post('/api/users/', payload)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['region'] == supervisor_user.region_id


# ---------------------------------------------------------------------------
# Avatar actions
#
# NOTE: upload_avatar (POST) and delete_avatar (DELETE) share url_path='avatar'.
# Due to a DRF router limitation, both generate identical URL regexes.  Django
# resolves to the first registered pattern (delete_avatar), so POST requests
# to /api/users/{id}/avatar currently receive 405 Method Not Allowed.  These
# tests document the intended behaviour with @pytest.mark.xfail so they will
# start passing once the URL conflict is resolved.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUploadAvatar:
    def _make_image(self, content_type='image/jpeg'):
        return SimpleUploadedFile(
            'avatar.jpg',
            b'\xff\xd8\xff\xe0' + b'\x00' * 100,
            content_type=content_type,
        )

    @pytest.mark.xfail(reason='POST /avatar returns 405 due to router URL conflict with DELETE /avatar')
    def test_upload_own_avatar(self, staff_user):
        client = _client_for(staff_user)
        avatar = self._make_image()
        resp = client.post(
            f'/api/users/{staff_user.id}/avatar',
            {'avatar': avatar},
            format='multipart',
        )
        assert resp.status_code == status.HTTP_200_OK

    @pytest.mark.xfail(reason='POST /avatar returns 405 due to router URL conflict with DELETE /avatar')
    def test_upload_other_user_avatar_non_admin_forbidden(self, staff_user, admin_user):
        client = _client_for(staff_user)
        avatar = self._make_image()
        resp = client.post(
            f'/api/users/{admin_user.id}/avatar',
            {'avatar': avatar},
            format='multipart',
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.xfail(reason='POST /avatar returns 405 due to router URL conflict with DELETE /avatar')
    def test_upload_avatar_invalid_file_type(self, staff_user):
        client = _client_for(staff_user)
        bad_file = SimpleUploadedFile(
            'avatar.txt', b'not an image', content_type='text/plain',
        )
        resp = client.post(
            f'/api/users/{staff_user.id}/avatar',
            {'avatar': bad_file},
            format='multipart',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.xfail(reason='POST /avatar returns 405 due to router URL conflict with DELETE /avatar')
    def test_upload_avatar_missing_file(self, staff_user):
        client = _client_for(staff_user)
        resp = client.post(
            f'/api/users/{staff_user.id}/avatar',
            {},
            format='multipart',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.xfail(reason='POST /avatar returns 405 due to router URL conflict with DELETE /avatar')
    def test_admin_can_upload_others_avatar(self, admin_user, staff_user):
        client = _client_for(admin_user)
        avatar = self._make_image()
        resp = client.post(
            f'/api/users/{staff_user.id}/avatar',
            {'avatar': avatar},
            format='multipart',
        )
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestSystemAvatar:
    def test_set_system_avatar_valid_key(self, staff_user):
        client = _client_for(staff_user)
        resp = client.post(
            f'/api/users/{staff_user.id}/system-avatar',
            {'system_avatar': 'geo-1'},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['system_avatar'] == 'geo-1'

    def test_set_system_avatar_invalid_key(self, staff_user):
        client = _client_for(staff_user)
        resp = client.post(
            f'/api/users/{staff_user.id}/system-avatar',
            {'system_avatar': 'invalid-key'},
            format='json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_set_system_avatar_non_owner_forbidden(self, staff_user, admin_user):
        # staff cannot set another user's system avatar → 403
        client = _client_for(staff_user)
        resp = client.post(
            f'/api/users/{admin_user.id}/system-avatar',
            {'system_avatar': 'geo-2'},
            format='json',
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_set_system_avatar_missing_field(self, staff_user):
        client = _client_for(staff_user)
        resp = client.post(
            f'/api/users/{staff_user.id}/system-avatar',
            {},
            format='json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
