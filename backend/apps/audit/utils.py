"""
审计日志工具函数
"""
from .models import AuditLog

# 审计快照中不得落库的敏感键与 Django 内部属性
SENSITIVE_KEYS = {'password'}
CLEARED_KEYS = {'phone', 'user_phone'}
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
            elif key in CLEARED_KEYS:
                data[key] = ''
            else:
                mask_sensitive(data[key])
    elif isinstance(data, list):
        for item in data:
            mask_sensitive(item)
    return data


def _clear_phone_value(data, phone):
    if not phone:
        return False
    if isinstance(data, dict):
        changed = False
        for key, value in list(data.items()):
            if value == phone:
                data[key] = ''
                changed = True
            elif _clear_phone_value(value, phone):
                changed = True
        return changed
    if isinstance(data, list):
        changed = False
        for value in data:
            changed = _clear_phone_value(value, phone) or changed
        return changed
    return False


def clear_user_phone_snapshots(user, batch_size=500):
    """Remove a deleted employee's phone from audit fields and nested snapshots."""
    from .models import AuditLog

    pending = []
    for log in AuditLog.objects.only(
        'id', 'user_id', 'user_phone', 'before_data', 'after_data',
    ).iterator(chunk_size=batch_size):
        changed = False
        if user.phone and log.user_phone == user.phone:
            log.user_phone = ''
            changed = True
        if _clear_phone_value(log.before_data, user.phone):
            changed = True
        if _clear_phone_value(log.after_data, user.phone):
            changed = True
        if changed:
            pending.append(log)
        if len(pending) >= batch_size:
            AuditLog.objects.bulk_update(pending, ['user_phone', 'before_data', 'after_data'])
            pending.clear()
    if pending:
        AuditLog.objects.bulk_update(pending, ['user_phone', 'before_data', 'after_data'])


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
