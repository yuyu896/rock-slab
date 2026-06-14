"""
Tests for Notification and ApprovalCC views: list, unread_count,
mark_read, mark_all_read, by_type, and CC endpoints.
"""
import pytest
from conftest import _client_for


NOTIFICATION_URL = '/api/notifications/'
CC_URL = '/api/notifications/cc/'


def _make_notification(recipient, **overrides):
    from apps.notifications.models import Notification
    defaults = dict(
        recipient=recipient,
        notification_type='system',
        title='测试通知',
        content='测试内容',
        priority='medium',
    )
    defaults.update(overrides)
    return Notification.objects.create(**defaults)


def _make_cc(recipient, **overrides):
    from apps.notifications.models import ApprovalCC
    defaults = dict(
        recipient=recipient,
        cc_type='auto',
        cc_reason='测试抄送',
    )
    defaults.update(overrides)
    return ApprovalCC.objects.create(**defaults)


# ---------------------------------------------------------------------------
# NotificationViewSet -- list & filtering
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNotificationList:
    def test_list_returns_own_notifications_only(self, staff_user, admin_user):
        _make_notification(staff_user, title='属于专员')
        _make_notification(admin_user, title='属于管理员')
        client = _client_for(staff_user)
        resp = client.get(NOTIFICATION_URL)
        assert resp.status_code == 200
        data = resp.json()
        titles = [r['title'] for r in data['results']]
        assert '属于专员' in titles
        assert '属于管理员' not in titles

    def test_list_paginated(self, admin_user):
        _make_notification(admin_user)
        client = _client_for(admin_user)
        resp = client.get(NOTIFICATION_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert 'count' in data
        assert 'results' in data

    def test_filter_by_notification_type(self, staff_user):
        _make_notification(staff_user, notification_type='approval', title='审批类')
        _make_notification(staff_user, notification_type='task', title='任务类')
        client = _client_for(staff_user)
        resp = client.get(NOTIFICATION_URL, {'notification_type': 'approval'})
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 1
        assert data['results'][0]['title'] == '审批类'


# ---------------------------------------------------------------------------
# NotificationViewSet -- unread_count
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUnreadCount:
    def test_unread_count_correct(self, staff_user):
        _make_notification(staff_user, is_read=False)
        _make_notification(staff_user, is_read=False)
        _make_notification(staff_user, is_read=True)
        client = _client_for(staff_user)
        resp = client.get(f'{NOTIFICATION_URL}unread_count/')
        assert resp.status_code == 200
        assert resp.json()['count'] == 2

    def test_unread_count_excludes_other_users(self, staff_user, admin_user):
        _make_notification(staff_user, is_read=False)
        _make_notification(admin_user, is_read=False)
        client = _client_for(staff_user)
        resp = client.get(f'{NOTIFICATION_URL}unread_count/')
        assert resp.status_code == 200
        assert resp.json()['count'] == 1


# ---------------------------------------------------------------------------
# NotificationViewSet -- mark_read
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMarkRead:
    def test_mark_single_read(self, staff_user):
        n = _make_notification(staff_user, is_read=False)
        client = _client_for(staff_user)
        resp = client.post(f'{NOTIFICATION_URL}{n.id}/mark_read/')
        assert resp.status_code == 200
        assert resp.json()['isRead'] is True
        n.refresh_from_db()
        assert n.is_read is True
        assert n.read_at is not None

    def test_mark_read_updates_unread_count(self, staff_user):
        n = _make_notification(staff_user, is_read=False)
        client = _client_for(staff_user)
        # Before marking
        resp = client.get(f'{NOTIFICATION_URL}unread_count/')
        assert resp.json()['count'] == 1
        # Mark as read
        client.post(f'{NOTIFICATION_URL}{n.id}/mark_read/')
        # After marking
        resp = client.get(f'{NOTIFICATION_URL}unread_count/')
        assert resp.json()['count'] == 0


# ---------------------------------------------------------------------------
# NotificationViewSet -- mark_all_read
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMarkAllRead:
    def test_mark_all_read(self, staff_user):
        _make_notification(staff_user, is_read=False)
        _make_notification(staff_user, is_read=False)
        _make_notification(staff_user, is_read=True)
        client = _client_for(staff_user)
        resp = client.post(f'{NOTIFICATION_URL}mark_all_read/')
        assert resp.status_code == 200
        assert resp.json()['updated'] == 2
        # Verify all are read now
        resp = client.get(f'{NOTIFICATION_URL}unread_count/')
        assert resp.json()['count'] == 0


# ---------------------------------------------------------------------------
# NotificationViewSet -- by_type
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestByType:
    def test_by_type_stats(self, staff_user):
        _make_notification(staff_user, notification_type='approval', is_read=False)
        _make_notification(staff_user, notification_type='approval', is_read=True)
        _make_notification(staff_user, notification_type='task', is_read=False)
        client = _client_for(staff_user)
        resp = client.get(f'{NOTIFICATION_URL}by_type/')
        assert resp.status_code == 200
        stats = resp.json()
        stats_map = {s['notificationType']: s for s in stats}
        assert stats_map['approval']['total'] == 2
        assert stats_map['approval']['unread'] == 1
        assert stats_map['task']['total'] == 1
        assert stats_map['task']['unread'] == 1

    def test_by_type_excludes_other_users(self, staff_user, admin_user):
        _make_notification(staff_user, notification_type='system')
        _make_notification(admin_user, notification_type='system')
        client = _client_for(staff_user)
        resp = client.get(f'{NOTIFICATION_URL}by_type/')
        assert resp.status_code == 200
        stats = resp.json()
        system_stat = [s for s in stats if s['notificationType'] == 'system'][0]
        assert system_stat['total'] == 1


# ---------------------------------------------------------------------------
# ApprovalCCViewSet -- list
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApprovalCCList:
    def test_manager_sees_own_cc_records(self, manager_user):
        _make_cc(manager_user)
        client = _client_for(manager_user)
        resp = client.get(CC_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 1

    def test_staff_forbidden_from_cc(self, staff_user):
        client = _client_for(staff_user)
        resp = client.get(CC_URL)
        assert resp.status_code == 403

    def test_cc_list_only_own_records(self, manager_user, admin_user):
        _make_cc(manager_user, cc_reason='经理的抄送')
        _make_cc(admin_user, cc_reason='管理员的抄送')
        client = _client_for(manager_user)
        resp = client.get(CC_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 1
        assert data['results'][0]['ccReason'] == '经理的抄送'


# ---------------------------------------------------------------------------
# ApprovalCCViewSet -- mark_read
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApprovalCCMarkRead:
    def test_mark_single_cc_read(self, manager_user):
        cc = _make_cc(manager_user, is_read=False)
        client = _client_for(manager_user)
        resp = client.post(f'{CC_URL}{cc.id}/mark_read/')
        assert resp.status_code == 200
        assert resp.json()['isRead'] is True
        cc.refresh_from_db()
        assert cc.is_read is True
        assert cc.read_at is not None

    def test_mark_all_cc_read(self, manager_user):
        _make_cc(manager_user, is_read=False)
        _make_cc(manager_user, is_read=False)
        client = _client_for(manager_user)
        resp = client.post(f'{CC_URL}mark_all_read/')
        assert resp.status_code == 200
        assert resp.json()['updated'] == 2
