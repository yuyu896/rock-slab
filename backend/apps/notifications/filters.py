import django_filters as df
from .models import Notification, ApprovalCC


class NotificationFilterSet(df.FilterSet):
    """通知过滤器"""
    notification_type = df.CharFilter(field_name='notification_type')
    is_read = df.BooleanFilter(field_name='is_read')
    priority = df.CharFilter(field_name='priority')

    class Meta:
        model = Notification
        fields = ['notification_type', 'is_read', 'priority']


class ApprovalCCFilterSet(df.FilterSet):
    """抄送记录过滤器"""
    cc_type = df.CharFilter(field_name='cc_type')
    is_read = df.BooleanFilter(field_name='is_read')

    class Meta:
        model = ApprovalCC
        fields = ['cc_type', 'is_read']
