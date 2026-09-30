"""Authentication tests: login, logout, token expiry, password change."""
import pytest
from django.utils import timezone
from rest_framework import status

from apps.authentication.models import ExpiringToken


@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, api_client, admin_user):
        resp = api_client.post('/api/auth/login/', {'phone': '13900000000', 'password': 'test123456'})
        assert resp.status_code == status.HTTP_200_OK
        assert 'token' in resp.data
        assert 'user' in resp.data
        assert resp.data['user']['phone'] == '13900000000'

    def test_login_wrong_password(self, api_client, admin_user):
        resp = api_client.post('/api/auth/login/', {'phone': '13900000000', 'password': 'wrong'})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client, db):
        resp = api_client.post('/api/auth/login/', {'phone': '19999999999', 'password': 'test123456'})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_invalid_phone_format(self, api_client, db):
        resp = api_client.post('/api/auth/login/', {'phone': '123', 'password': 'test123456'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_missing_fields(self, api_client, db):
        resp = api_client.post('/api/auth/login/', {})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_inactive_user(self, api_client, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.create_user(phone='13900000099', name='Inactive', password='test123456', status='inactive')
        resp = api_client.post('/api/auth/login/', {'phone': '13900000099', 'password': 'test123456'})
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
        resp = api_client.get('/api/auth/profile/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_valid_token_accepted(self, authenticated_client):
        resp = authenticated_client.get('/api/auth/profile/')
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestSessionPolicy:
    def test_token_validity_is_seven_days(self, admin_user):
        # TOKEN_EXPIRATION_DAYS=7 通过模型 save 写入 expires_at
        now = timezone.now()
        token = ExpiringToken.objects.create(user=admin_user)
        lower = now + timezone.timedelta(days=7, minutes=-1)
        upper = now + timezone.timedelta(days=7, minutes=1)
        assert lower <= token.expires_at <= upper

    def test_no_sliding_renewal(self, authenticated_client, admin_user):
        # 使用 Token 请求不会延长 expires_at（固定有效期）
        token = ExpiringToken.objects.get(user=admin_user)
        before = token.expires_at
        resp = authenticated_client.get('/api/auth/profile/')
        assert resp.status_code == status.HTTP_200_OK
        token.refresh_from_db()
        assert token.expires_at == before

    def test_new_login_invalidates_previous_session(self, api_client, admin_user):
        from django.core.cache import cache
        cache.clear()  # 重置限流/锁定计数，隔离跨测试影响
        resp1 = api_client.post('/api/auth/login/', {'phone': '13900000000', 'password': 'test123456'})
        token1 = resp1.data['token']

        # 旧会话可用
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token1}')
        assert api_client.get('/api/auth/profile/').status_code == status.HTTP_200_OK

        # 同一账号再次登录 → 签发新 Token，旧 Token 立即失效（单会话强制）
        resp2 = api_client.post('/api/auth/login/', {'phone': '13900000000', 'password': 'test123456'})
        token2 = resp2.data['token']
        assert token2 != token1

        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token1}')
        assert api_client.get('/api/auth/profile/').status_code == status.HTTP_401_UNAUTHORIZED

        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token2}')
        assert api_client.get('/api/auth/profile/').status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPasswordChange:
    def test_change_password_success(self, authenticated_client, admin_user):
        # Save token key before request (credentials() returns None after DRF update)
        old_token = ExpiringToken.objects.get(user=admin_user)
        old_token_key = old_token.key

        resp = authenticated_client.put('/api/auth/password/', {
            'oldPassword': 'test123456',
            'newPassword': 'newpass123456',
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert 'token' in resp.data  # New token returned

        # Old token should no longer exist
        assert ExpiringToken.objects.filter(key=old_token_key).exists() is False

    def test_change_password_wrong_old(self, authenticated_client):
        resp = authenticated_client.put('/api/auth/password/', {
            'oldPassword': 'wrongold',
            'newPassword': 'newpass123456',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_weak_rejected(self, authenticated_client, admin_user):
        # 新密码不满足最小长度（8 位），应被密码校验器拒绝且不修改密码
        resp = authenticated_client.put('/api/auth/password/', {
            'oldPassword': 'test123456',
            'newPassword': '123',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        admin_user.refresh_from_db()
        assert admin_user.check_password('test123456')


@pytest.mark.django_db
class TestAccountLockout:
    def test_lockout_after_threshold(self, db):
        from django.core.cache import cache
        from apps.authentication.account_lockout import (
            record_login_failure, is_account_locked, check_account_locked,
            clear_login_failures, FAILURES_THRESHOLD,
        )
        cache.clear()
        phone = '13900000999'
        for _ in range(FAILURES_THRESHOLD - 1):
            record_login_failure(phone)
        assert not is_account_locked(phone)
        record_login_failure(phone)  # 达阈值 → 锁定
        assert is_account_locked(phone)
        assert check_account_locked(phone).status_code == 403
        # clear 只清失败计数；锁定由独立 TTL 控制，窗口内仍锁定
        clear_login_failures(phone)
        assert is_account_locked(phone)
        cache.clear()

    def test_clear_resets_failure_count(self, db):
        from django.core.cache import cache
        from apps.authentication.account_lockout import (
            record_login_failure, is_account_locked, clear_login_failures,
        )
        cache.clear()
        phone = '13900000998'
        for _ in range(3):
            record_login_failure(phone)
        clear_login_failures(phone)  # 未达阈值前清零
        for _ in range(3):
            record_login_failure(phone)
        assert not is_account_locked(phone)  # 累计仍 < 阈值，未锁定
        cache.clear()


@pytest.mark.django_db
class TestAccountSafetyHardening:
    """account-safety-hardening：计数原子性 / 改密失败审计 / 健康端点。"""

    def test_login_failure_count_atomic_incr(self):
        from apps.authentication.account_lockout import record_login_failure, FAILURES_THRESHOLD
        from django.core.cache import cache
        cache.clear()
        for _ in range(FAILURES_THRESHOLD):
            record_login_failure('13866667777')
        # 10 次原子自增后计数恰为阈值（无丢失），账号进入锁定
        assert cache.get('rock_slab:login_fail:13866667777') == FAILURES_THRESHOLD
        assert cache.get('rock_slab:login_lock:13866667777') is True

    def test_change_password_wrong_old_audited_as_failure(self, api_client, staff_user):
        from apps.audit.models import AuditLog
        from conftest import _client_for
        client = _client_for(staff_user)
        resp = client.put('/api/auth/password/', {
            'oldPassword': 'wrong-old-pwd', 'newPassword': 'brandnew123456',
        }, format='json')
        assert resp.status_code == 400
        log = AuditLog.objects.filter(
            action='change_password', user=staff_user,
        ).order_by('-created_at').first()
        assert log is not None
        assert log.is_success is False  # 4xx 记失败（不再误记成功）

    def test_health_error_no_detail_leak(self):
        from unittest import mock
        from django.test import Client
        with mock.patch('django.db.connection.ensure_connection', side_effect=RuntimeError('psql://secret@10.0.0.1:5432 boom')):
            resp = Client().get('/api/health/')
        assert resp.status_code == 503
        assert resp.json() == {'status': 'error'}
        assert b'secret' not in resp.content
