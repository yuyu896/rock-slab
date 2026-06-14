"""
审计日志 Signals
自动记录用户登录/登出等操作
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from apps.authentication.models import ExpiringToken
from .models import AuditLog

User = get_user_model()


@receiver(post_save, sender=ExpiringToken)
def log_login(sender, instance, created, **kwargs):
    """记录用户登录"""
    if created:
        user = instance.user
        AuditLog.objects.create(
            user=user,
            user_name=user.name,
            user_phone=user.phone,
            action='login',
            resource_type='Token',
            resource_id=None,
            resource_name=f'Token for {user.name}',
            description=f'{user.name} 登录系统',
            is_success=True,
        )
