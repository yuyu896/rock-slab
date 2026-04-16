"""Authentication tests: login, logout, token expiry, password change."""
import pytest
from django.utils import timezone
from rest_framework import status

from apps.authentication.models import ExpiringToken


@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, api_client, admin_user):
        resp = api_client.post('/api/auth/login', {'phone': '13900000000', 'password': 'test123456'})
        assert resp.status_code == status.HTTP_200_OK
        assert 'token' in resp.data
        assert 'user' in resp.data
        assert resp.data['user']['phone'] == '13900000000'

    def test_login_wrong_password(self, api_client, admin_user):
        resp = api_client.post('/api/auth/login', {'phone': '13900000000', 'password': 'wrong'})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client, db):
        resp = api_client.post('/api/auth/login', {'phone': '19999999999', 'password': 'test123456'})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_invalid_phone_format(self, api_client, db):
        resp = api_client.post('/api/auth/login', {'phone': '123', 'password': 'test123456'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_missing_fields(self, api_client, db):
        resp = api_client.post('/api/auth/login', {})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_inactive_user(self, api_client, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.create_user(phone='13900000099', name='Inactive', password='test123456', status='inactive')
        resp = api_client.post('/api/auth/login', {'phone': '13900000099', 'password': 'test123456'})
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestTokenExpiry:
    def test_token_has_expires_at(self, admin_user):
        token = ExpiringToken.objects.create(user=admin_user)
        assert token.expires_at is not None
        assert token.expires_at > timezone.now()

    def test_expired_token_rejected(self, api_client, admin_user):
        token = ExpiringToken.objects.create(user=admin_user)
        token.expires_at = timezone.now() - timezone.timedelta(days=1)
        token.save(update_fields=['expires_at'])

        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        resp = api_client.get('/api/auth/profile')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_valid_token_accepted(self, authenticated_client):
        resp = authenticated_client.get('/api/auth/profile')
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPasswordChange:
    def test_change_password_success(self, authenticated_client, admin_user):
        resp = authenticated_client.put('/api/auth/password', {
            'oldPassword': 'test123456',
            'newPassword': 'newpass123456',
        })
        assert resp.status_code == status.HTTP_200_OK
        assert 'token' in resp.data  # New token returned

        # Old token should no longer work
        old_token_key = authenticated_client.credentials()['HTTP_AUTHORIZATION'].replace('Token ', '')
        assert ExpiringToken.objects.filter(key=old_token_key).exists() is False

    def test_change_password_wrong_old(self, authenticated_client):
        resp = authenticated_client.put('/api/auth/password', {
            'oldPassword': 'wrongold',
            'newPassword': 'newpass123456',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
