"""
审计日志装饰器
用于在 ViewSet 中记录操作日志
"""
import json
from functools import wraps
from .models import AuditLog
from .utils import get_request_info


def audit_log(action, resource_type=None, description_template=None):
    """
    审计日志装饰器

    用法:
    @audit_log(action='create', resource_type='Asset')
    def perform_create(self, serializer):
        ...

    @audit_log(action='approve', resource_type='Transfer', description_template='审批通过调拨单')
    def approve(self, request, pk=None):
        ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取 view 和 request 对象
            view = args[0] if args else None
            request = getattr(view, 'request', None)

            # 记录执行前状态（用于 update 操作）
            before_data = None
            instance_before = None
            if action == 'update' and hasattr(view, 'get_object'):
                try:
                    instance_before = view.get_object()
                    if hasattr(instance_before, '__dict__'):
                        before_data = json.loads(json.dumps(
                            instance_before.__dict__,
                            default=str
                        ))
                except Exception:
                    pass

            # 执行原函数
            result = None
            error_msg = ''
            is_success = True

            try:
                result = func(*args, **kwargs)
            except Exception as e:
                is_success = False
                error_msg = str(e)
                raise
            finally:
                # 记录日志
                if request and request.user.is_authenticated:
                    # 获取资源信息
                    resource_id = None
                    resource_name = ''
                    after_data = None

                    # 从返回结果中提取信息
                    if result and hasattr(result, 'data'):
                        data = result.data if hasattr(result, 'data') else {}
                        if isinstance(data, dict):
                            resource_id = data.get('id')
                            resource_name = data.get('name') or data.get('资产名称', '') or data.get('title', '')

                            # 深拷贝后数据
                            try:
                                after_data = json.loads(json.dumps(data, default=str))
                            except Exception:
                                after_data = data

                    # 如果没有从结果获取到，尝试从实例获取
                    if not resource_id and instance_before:
                        resource_id = getattr(instance_before, 'id', None)
                        resource_name = getattr(instance_before, 'name', '') or str(instance_before)

                    # 构建 description
                    description = description_template or f'{action} {resource_type or "resource"}'
                    if resource_name:
                        description = f'{description}: {resource_name}'

                    # 获取请求信息
                    request_info = get_request_info(request)

                    # 创建日志
                    AuditLog.objects.create(
                        user=request.user,
                        user_name=request.user.name,
                        user_phone=request.user.phone,
                        action=action,
                        resource_type=resource_type or (view.__class__.__name__ if view else 'Unknown'),
                        resource_id=resource_id,
                        resource_name=resource_name[:200] if resource_name else '',
                        description=description,
                        before_data=before_data,
                        after_data=after_data,
                        is_success=is_success,
                        error_message=error_msg,
                        **request_info
                    )

            return result
        return wrapper
    return decorator


def audit_create(resource_type=None):
    """创建操作日志装饰器"""
    return audit_log(action='create', resource_type=resource_type)


def audit_update(resource_type=None):
    """更新操作日志装饰器"""
    return audit_log(action='update', resource_type=resource_type)


def audit_delete(resource_type=None):
    """删除操作日志装饰器"""
    return audit_log(action='delete', resource_type=resource_type)


def audit_approve(resource_type=None):
    """审批操作日志装饰器"""
    return audit_log(action='approve', resource_type=resource_type)


def audit_reject(resource_type=None):
    """驳回操作日志装饰器"""
    return audit_log(action='reject', resource_type=resource_type)


def audit_export(resource_type=None):
    """导出操作日志装饰器"""
    return audit_log(action='export', resource_type=resource_type)


def audit_import(resource_type=None):
    """导入操作日志装饰器"""
    return audit_log(action='import', resource_type=resource_type)
