from rest_framework.permissions import BasePermission


class OperationPermission(BasePermission):
    """基于业务操作授权的接口级权限。

    在 ViewSet 上声明所需操作码：
        required_operation = 'manage_assets'                   # 类级默认
        required_operations = {'approve': 'approve_transfer'}  # 按 action 细分

    admin 恒真；其余用户需持有对应 OperationGrant。
    未声明操作码时放行（用于读操作，数据范围仍由 DataScopeMixin 控制）。
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        action = getattr(view, 'action', None)
        required = (getattr(view, 'required_operations', None) or {}).get(action)
        if required is None:
            required = getattr(view, 'required_operation', None)
        if not required:
            return True
        return user.can(required)
