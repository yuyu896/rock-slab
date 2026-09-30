"""
审计日志工具函数
"""
from .models import AuditLog

# 审计快照中不得落库的敏感键（值替换为掩码）与 Django 内部属性（直接剔除）
SENSITIVE_KEYS = {'password'}
_INTERNAL_KEYS = {'_state'}
_MASK_VALUE = '***'


def mask_sensitive(data):
    """递归脱敏：敏感键值替换为 '***'，剔除 Django 内部属性（原地修改并返回）。

    before_data / after_data 均为 JSON 结构（dict/list 嵌套）；键命中即替换，
    与值的形态无关，避免按哈希格式探测的假阴性。
    """
    if isinstance(data, dict):
        for key in list(data.keys()):
            if key in _INTERNAL_KEYS:
                del data[key]
            elif key in SENSITIVE_KEYS:
                data[key] = _MASK_VALUE
            else:
                mask_sensitive(data[key])
    elif isinstance(data, list):
        for item in data:
            mask_sensitive(item)
    return data


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
