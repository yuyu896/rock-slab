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
    def test_transfer_skips_out_of_scope_approver(
        self, admin_user, branch, supervisor_user, supervisor_b,
    ):
        """调拨只通知对调出分公司有授权的审批人：区域内主管收到，区域 B 主管不收到。"""
        from apps.categories.models import Category
        from apps.notifications.models import Notification
        client = _client_for(admin_user)
        item = Category.objects.get(asset_code='NOTIF-SCOPE-001')
        resp = client.post('/api/transfers/transfer', {
            '调拨日期': '2026-01-15',
            '调出分公司': branch.name, '调入分公司': branch.name,
            'items': [{'item': str(item.id), '数量': 1}],
        }, format='json')
        assert resp.status_code == 201
        tid = resp.data['id']
        # supervisor_user 对 branch 有授权 → 收到审批通知（P2 明细摘要：首行品目 + 合计数量 + 单据编号）
        notif = Notification.objects.get(recipient=supervisor_user, related_object_id=tid)
        assert '待审批' in notif.title
        assert notif.extra_data['asset_code'] == 'NOTIF-SCOPE-001'
        assert notif.extra_data['qty'] == 1
        assert notif.extra_data['doc_number'] == resp.data['单据编号']
        # supervisor_b 对 branch 无授权 → 不收到该调拨的审批通知
        assert not Notification.objects.filter(recipient=supervisor_b, related_object_id=tid).exists()
