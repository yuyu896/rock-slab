"""岗位模板注册表 —— 岗位 = 权限预填模板（仅预填，不参与运行时鉴权）。

口诀：岗位定操作、任命定范围、特例才单独授予。
- operations：该岗位分配时预填勾选的业务操作码（None 表示全部，admin 运行时恒真无需授予）
- scope_type：该岗位通常的任命节点类型提示（分配页第③步默认节点类型）

模板只做预填：保存仍写 OperationGrant 表，后续单独增删不回写模板；
运行时鉴权只看授权表与 admin 身份（User.can / OperationPermission）。
"""

POSITION_TEMPLATES = {
    'admin': {
        'label': '系统管理员',
        'scope_type': 'all',
        'operations': None,  # 全部权限内置，无需授予
    },
    'director': {
        'label': '大区负责人',
        'scope_type': 'region',
        'operations': [
            'manage_users',
            'manage_organizations',
            'manage_dictionary',
            'manage_assets',
            'approve_transfer',
            'approve_inventory',
            'view_all_notifications',
            'view_reports',
        ],
    },
    'manager': {
        'label': '分公司行政',
        'scope_type': 'branch',
        'operations': [
            'manage_users',
            'manage_dictionary',
            'manage_assets',
            'approve_transfer',
            'approve_inventory',
            'adjust_ledger',
            'manage_instances',
            'view_reports',
        ],
    },
    'leader': {
        'label': '行政组长',
        'scope_type': 'team',
        'operations': [],
    },
}

# 存量岗位 → 目标岗位映射（migrate_positions 用；supervisor/staff 退役默认去向 manager）
LEGACY_POSITION_MAP = {
    'supervisor': 'manager',
    'staff': 'manager',
}


def position_template(role):
    return POSITION_TEMPLATES.get(role)


def template_operations(role):
    """岗位模板预填操作码清单；admin 返回 None（全部，无需授予）；未知岗位返回空清单。"""
    tpl = position_template(role)
    if tpl is None:
        return []
    return tpl['operations']
