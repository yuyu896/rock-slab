from rest_framework.permissions import BasePermission


class OperationPermission(BasePermission):
    """基于业务操作授权的接口级权限。

    在 ViewSet 上声明所需操作码：
        required_operation = 'view_instances'             # 类级默认
        required_operations = {'approve': 'approve_purchase'}  # 按 action 细分

    admin 恒真；其余用户需持有对应 OperationGrant。
    未声明操作码时不执行业务操作授权；数据范围仍由对应 queryset/mixin 控制。
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        any_resolver = getattr(view, 'get_required_operations_any', None)
        if callable(any_resolver):
            required_any = any_resolver(request)
            if required_any is not None:
                return bool(required_any) and any(user.can(code) for code in required_any)
        plural_resolver = getattr(view, 'get_required_operations', None)
        if callable(plural_resolver):
            required = plural_resolver(request)
            if not required:
                return True
            if isinstance(required, str):
                required = [required]
            return all(user.can(code) for code in required)
        resolver = getattr(view, 'get_required_operation', None)
        if callable(resolver):
            required = resolver(request)
            if not required:
                return True
            if isinstance(required, str):
                required = [required]
            return all(user.can(code) for code in required)
        action = getattr(view, 'action', None)
        required = (getattr(view, 'required_operations', None) or {}).get(action)
        if required is None:
            required = getattr(view, 'required_operation', None)
        if not required:
            return True
        if isinstance(required, str):
            required = [required]
        return all(user.can(code) for code in required)
