"""业务操作码注册表 —— 管理权限的「业务操作」维度。

与各 ViewSet 的 required_operation / required_operations 对应。
新增操作时在此登记即可；前后端可共享此清单。
"""

# 操作码 → 中文说明
OPERATIONS = {
    'manage_users': '管理用户',
    'manage_organizations': '管理组织架构',
    'manage_categories': '管理资产分类',
    'manage_assets': '管理资产（增删改/导入）',
    'approve_transfer': '审批资产流转',
    'approve_inventory': '审批盘点任务',
    'view_audit': '查看审计日志',
    'view_all_notifications': '查看抄送记录',
    'view_reports': '查看统计报表',
}

OPERATION_CHOICES = [(code, label) for code, label in OPERATIONS.items()]


def is_valid_operation(code: str) -> bool:
    return code in OPERATIONS
