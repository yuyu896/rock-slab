"""
审计日志工具函数
"""
from .models import AuditLog


def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def get_request_info(request):
    """获取请求信息"""
    return {
        'ip_address': get_client_ip(request),
        'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
        'request_path': request.path[:500],
        'request_method': request.method,
    }


def create_audit_log(request, action, resource_type, resource_id=None,
                     resource_name='', description='', before_data=None,
                     after_data=None, is_success=True, error_message=''):
    """创建审计日志"""
    user = request.user if request.user.is_authenticated else None
    request_info = get_request_info(request)

    return AuditLog.objects.create(
        user=user,
        user_name=user.name if user else '',
        user_phone=user.phone if user else '',
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        description=description,
        before_data=before_data,
        after_data=after_data,
        is_success=is_success,
        error_message=error_message,
        **request_info
    )
