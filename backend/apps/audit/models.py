from django.db import models
from core.models import UUIDModel, TimestampedModel


class AuditLog(UUIDModel, TimestampedModel):
    """操作日志"""
    ACTION_CHOICES = [
        ('login', '登录'),
        ('logout', '登出'),
        ('create', '创建'),
        ('update', '更新'),
        ('delete', '删除'),
        ('approve', '审批通过'),
        ('reject', '审批驳回'),
        ('export', '导出'),
        ('import', '导入'),
        ('view', '查看'),
    ]

    # 操作人
    user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='audit_logs',
        verbose_name='操作人',
    )
    user_name = models.CharField('操作人姓名', max_length=100, blank=True)
    user_phone = models.CharField('操作人手机', max_length=20, blank=True)

    # 操作信息
    action = models.CharField(
        '操作类型', max_length=20,
        choices=ACTION_CHOICES,
    )
    resource_type = models.CharField(
        '资源类型', max_length=50,
    )
    resource_id = models.UUIDField(
        '资源ID', null=True, blank=True,
    )
    resource_name = models.CharField(
        '资源名称', max_length=200, blank=True,
    )

    # 详情
    description = models.TextField('操作描述', blank=True)
    before_data = models.JSONField(
        '变更前数据', null=True, blank=True,
    )
    after_data = models.JSONField(
        '变更后数据', null=True, blank=True,
    )

    # 请求信息
    ip_address = models.GenericIPAddressField(
        'IP地址', null=True, blank=True,
    )
    user_agent = models.CharField(
        '用户代理', max_length=500, blank=True,
    )
    request_path = models.CharField(
        '请求路径', max_length=500, blank=True,
    )
    request_method = models.CharField(
        '请求方法', max_length=10, blank=True,
    )

    # 结果
    is_success = models.BooleanField('是否成功', default=True)
    error_message = models.TextField('错误信息', blank=True)

    class Meta:
        db_table = 'audit_log'
        ordering = ['-created_at']
        verbose_name = '审计日志'
        verbose_name_plural = '审计日志'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user_name} - {self.get_action_display()} - {self.resource_type}'
