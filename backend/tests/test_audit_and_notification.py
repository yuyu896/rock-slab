"""
审计完整性与通知数据范围测试（audit-log-completeness / notification-data-scoping）。
"""
import pytest
from conftest import _client_for


@pytest.mark.django_db
class TestAuditLogCompleteness:
    def test_change_password_is_audited(self, staff_user):
        """改密（函数视图）被写入审计日志——验证 audit_log 装饰器兼容 FBV。"""
        from apps.audit.models import AuditLog
        client = _client_for(staff_user)
        resp = client.put('/api/auth/password/', {
            'oldPassword': 'test123456', 'newPassword': 'newpass123',
        }, format='json')
        assert resp.status_code == 200
        assert AuditLog.objects.filter(user=staff_user, action='change_password').exists()


@pytest.mark.django_db
class TestNotificationDataScoping:
    def test_transfer_skips_out_of_scope_approver(self, admin_user, branch, supervisor_b):
        """调拨只通知对调出分公司有授权的审批人，区域 B 主管不收到。"""
        from apps.notifications.models import Notification
        client = _client_for(admin_user)
        resp = client.post('/api/transfers/transfer', {
            '调拨日期': '2026-01-15', '资产编号': 'NOTIF-SCOPE-001', '资产名称': '通知范围测试',
            '调出分公司': branch.name, '调入分公司': branch.name,
            '调拨数量': 1, 'action_type': 'transfer',
        }, format='json')
        assert resp.status_code == 201
        tid = resp.data['id']
        # supervisor_b 对 branch 无授权 → 不收到该调拨的审批通知
        assert not Notification.objects.filter(recipient=supervisor_b, related_object_id=tid).exists()
