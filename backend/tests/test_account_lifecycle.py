"""
账号生命周期安全测试（account-lifecycle-security）。

覆盖：密码 update 路径不得绕过 set_password（防账号接管）、建号密码必填 + 强度校验、
停用账号联动失效 token。
"""
import pytest
from conftest import _client_for


@pytest.mark.django_db
class TestAccountLifecycleSecurity:
    def test_update_ignores_password_field(self, admin_user, staff_user):
        """更新路径不接受 password：注入预生成哈希无法接管账号。"""
        from django.contrib.auth.hashers import make_password
        client = _client_for(admin_user)
        attacker_hash = make_password('attacker-known-123')
        resp = client.patch(f'/api/users/{staff_user.id}', {
            'password': attacker_hash,
        }, format='json')
        assert resp.status_code == 200
        staff_user.refresh_from_db()
        # password 未被原样写入：攻击者明文登录失败
        assert not staff_user.check_password('attacker-known-123')
        # 原密码仍有效（未被改动）
        assert staff_user.check_password('test123456')

    def test_create_without_password_rejected(self, admin_user):
        client = _client_for(admin_user)
        resp = client.post('/api/users/', {
            'phone': '13800007777', 'name': '无密码', 'role': 'staff',
        }, format='json')
        assert resp.status_code == 400

    def test_create_weak_password_rejected(self, admin_user):
        client = _client_for(admin_user)
        resp = client.post('/api/users/', {
            'phone': '13800007778', 'name': '弱密码', 'role': 'staff',
            'password': '123',
        }, format='json')
        assert resp.status_code == 400

    def test_disable_user_revokes_token(self, admin_user, staff_user):
        """停用账号（status=inactive）后旧 token 立即失效。"""
        from apps.authentication.models import ExpiringToken
        client_staff = _client_for(staff_user)  # 触发 token 创建
        assert client_staff.get('/api/auth/profile/').status_code == 200

        client_admin = _client_for(admin_user)
        resp = client_admin.patch(f'/api/users/{staff_user.id}', {
            'status': 'inactive',
        }, format='json')
        assert resp.status_code == 200

        # 存量 token 已删除
        assert not ExpiringToken.objects.filter(user=staff_user).exists()
        # 旧 token 调用 → 401
        assert client_staff.get('/api/auth/profile/').status_code == 401
