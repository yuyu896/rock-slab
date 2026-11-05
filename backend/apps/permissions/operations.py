"""中央权限目录；运行时校验和前端授权界面共用稳定操作码。"""

PERMISSION_CATALOG_VERSION = 2


def _op(
    code, label, module, module_label, description, *, prerequisites=(),
    conditional_prerequisites=None,
):
    return {
        'code': code,
        'label': label,
        'module': module,
        'module_label': module_label,
        'description': description,
        'catalog_version': PERMISSION_CATALOG_VERSION,
        'prerequisites': list(prerequisites),
        'conditional_prerequisites': {
            condition: list(codes)
            for condition, codes in (conditional_prerequisites or {}).items()
        },
    }


OPERATION_CATALOG = [
    _op('view_dashboard', '查看工作台', 'workbench', '工作台与通知', '查看工作台汇总数据和数据范围内的“待处理事项”。'),
    _op('view_notifications', '查看个人通知', 'workbench', '工作台与通知', '查看发送给本人的通知，并处理本人通知的已读状态。'),
    _op('view_approval_reports', '查看审批报告', 'workbench', '工作台与通知', '查看分配给本人的审批抄送记录及审批快照，并处理本人记录的已读状态。'),
    _op('view_reports', '查看统计报表', 'workbench', '工作台与通知', '查看数据范围内的统计报表和流转单据逐行明细；可访问工作台共享汇总接口，但不能进入工作台页面。'),

    _op('view_categories', '查看品目', 'dictionaries', '基础资料', '查看品目字典。'),
    _op('edit_categories', '编辑品目', 'dictionaries', '基础资料', '新增、修改、删除和导入品目；所有操作均要求同时持有“查看品目”。', prerequisites=('view_categories',)),
    _op('view_departments', '查看部门字典', 'dictionaries', '基础资料', '查看部门字典及表单选项。'),
    _op('edit_departments', '编辑部门', 'dictionaries', '基础资料', '新增、修改和删除部门字典项；所有操作均要求同时持有“查看部门字典”。', prerequisites=('view_departments',)),
    _op('view_suppliers', '查看供应商字典', 'dictionaries', '基础资料', '查看供应商字典及供应商信息。'),
    _op('edit_suppliers', '编辑供应商字典', 'dictionaries', '基础资料', '新增、修改和删除供应商字典项；所有操作均要求同时持有“查看供应商字典”。', prerequisites=('view_suppliers',)),

    _op('view_users', '查看员工账号', 'personnel', '员工与组织', '查看员工账号资料。'),
    _op('edit_users', '编辑员工账号', 'personnel', '员工与组织', '新增、修改和删除员工账号，包含删除本人；需同时持有“查看员工账号”。', prerequisites=('view_users',)),
    _op('view_organizations', '查看组织架构', 'personnel', '员工与组织', '查看组织节点及员工归属。'),
    _op('edit_organizations', '编辑组织节点', 'personnel', '员工与组织', '新增和修改组织节点；修改集团名称还要求全组织数据范围。需同时持有“查看组织架构”。', prerequisites=('view_organizations',)),
    _op('delete_organizations', '删除组织节点', 'personnel', '员工与组织', '删除组织节点；需同时持有“查看组织架构”，并受组织关联数据保护。', prerequisites=('view_organizations',)),

    _op('view_asset_ledger', '查看资产台账', 'asset_ledger', '资产台账', '查看授权数据范围内的资产结存和明细。'),
    _op('import_asset_ledger', '导入资产台账', 'asset_ledger', '资产台账', '预览并确认导入资产台账；需同时持有“查看资产台账”，盘点锁期间不得入账，任一行错误整份驳回。', prerequisites=('view_asset_ledger',)),
    _op('adjust_asset_ledger', '调整资产台账', 'asset_ledger', '资产台账', '创建台账手工调整；需同时持有“查看资产台账”，盘点锁期间不得入账。', prerequisites=('view_asset_ledger',)),
    _op('view_instances', '查看实例档案', 'instances', '实例档案', '查看授权数据范围内的固定资产实例和生平。'),
    _op('edit_instances', '编辑实例档案', 'instances', '实例档案', '编辑实例资料及图片；需同时持有“查看实例档案”和“查看供应商字典”。', prerequisites=('view_instances', 'view_suppliers')),
    _op('change_instance_assignee', '更换使用人和部门', 'instances', '实例档案', '按数据范围更换实例使用人或部门；需同时持有“查看实例档案”和“查看部门字典”。', prerequisites=('view_instances', 'view_departments')),
    _op('print_instance_label', '打印实例标签', 'instances', '实例档案', '打印实例标签；需同时持有“查看实例档案”。', prerequisites=('view_instances',)),

    _op('view_purchase', '查看采购入库单', 'purchase', '采购入库', '查看并导出当前数据范围内的采购入库单及供应商、单价和金额；草稿仅创建人可查看，系统管理员也不例外。'),
    _op('edit_purchase', '编辑采购入库单', 'purchase', '采购入库', '创建、编辑本人草稿或已驳回单据、提交/重提、撤回本人待审批单，并批量导入后提交审批；需同时持有“查看采购入库单”和“查看品目”。草稿仅创建人可查看、编辑和提交，系统管理员也不例外；管理员仍可编辑、重提他人已驳回单据。所有写操作限当前数据范围；导入任一行错误整份驳回。', prerequisites=('view_purchase', 'view_categories')),
    _op('delete_purchase_draft', '删除采购入库草稿', 'purchase', '采购入库', '仅删除当前数据范围内本人创建的草稿；系统管理员也不例外。需同时持有“查看采购入库单”。', prerequisites=('view_purchase',)),
    _op('approve_purchase', '审批采购入库单', 'purchase', '采购入库', '需同时持有“查看采购入库单”；分公司行政只能审批本人创建的待审批单，行政组长及以上可审批当前数据范围内的待审批单，系统管理员可审批任意待审批单。', prerequisites=('view_purchase',)),

    _op('view_assignment', '查看领用出库单', 'assignment', '领用出库', '查看当前数据范围内的领用出库单；草稿仅创建人可查看，系统管理员也不例外。'),
    _op('edit_assignment', '编辑领用出库单', 'assignment', '领用出库', '创建、编辑本人草稿或已驳回单据、提交/重提、撤回本人待审批单并批量导入；需同时持有“查看领用出库单”和“查看资产台账”。草稿仅创建人可查看、编辑和提交，系统管理员也不例外；管理员仍可编辑、重提他人已驳回单据。实例管理品目另需“查看实例档案”；导入任一行错误整份驳回。', prerequisites=('view_assignment', 'view_asset_ledger'), conditional_prerequisites={'选择实例管理品目': ('view_instances',)}),
    _op('delete_assignment_draft', '删除领用出库草稿', 'assignment', '领用出库', '仅删除当前数据范围内本人创建的草稿；系统管理员也不例外。需同时持有“查看领用出库单”。', prerequisites=('view_assignment',)),
    _op('approve_assignment', '审批领用出库单', 'assignment', '领用出库', '需同时持有“查看领用出库单”；分公司行政只能审批本人创建的待审批单，行政组长及以上可审批当前数据范围内的待审批单，系统管理员可审批任意待审批单。', prerequisites=('view_assignment',)),

    _op('view_transfer', '查看调拨单', 'transfer', '调拨', '调出或调入任一侧在当前数据范围内时，可查看整张调拨单；草稿仅创建人可查看，系统管理员也不例外。'),
    _op('edit_transfer', '编辑调拨单', 'transfer', '调拨', '创建、编辑本人草稿或已驳回单据、提交/重提、撤回本人待审批单、批量导入及拒收调入单据；需同时持有“查看调拨单”和“查看资产台账”。草稿仅创建人可查看、编辑和提交，系统管理员也不例外；管理员仍可编辑、重提他人已驳回单据。实例管理品目另需“查看实例档案”；导入任一行错误整份驳回。', prerequisites=('view_transfer', 'view_asset_ledger'), conditional_prerequisites={'选择实例管理品目': ('view_instances',)}),
    _op('delete_transfer_draft', '删除调拨草稿', 'transfer', '调拨', '仅删除当前数据范围内本人创建的草稿；系统管理员也不例外。需同时持有“查看调拨单”。', prerequisites=('view_transfer',)),
    _op('approve_internal_transfer', '审批调拨单', 'transfer', '调拨', '需同时持有“查看调拨单”；分公司行政只能审批本人创建的待审批单，行政组长及以上可审批当前数据范围内的待审批单，系统管理员可审批任意待审批单。', prerequisites=('view_transfer',)),

    _op('view_recovery', '查看回收单', 'recovery', '回收', '查看当前数据范围内的回收单；草稿仅创建人可查看，系统管理员也不例外。'),
    _op('view_recovery_ledger', '查看物资处置台账', 'recovery', '回收', '独立查看直接处置记录、处置金额汇总和导出。'),
    _op('edit_recovery', '编辑回收单', 'recovery', '回收', '创建、编辑本人草稿或已驳回单据、提交/重提并撤回本人待审批单；需同时持有“查看回收单”和“查看资产台账”。草稿仅创建人可查看、编辑和提交，系统管理员也不例外；管理员仍可编辑、重提他人已驳回单据。实例管理品目另需“查看实例档案”。', prerequisites=('view_recovery', 'view_asset_ledger'), conditional_prerequisites={'选择实例管理品目': ('view_instances',)}),
    _op('delete_recovery_draft', '删除回收草稿', 'recovery', '回收', '仅删除当前数据范围内本人创建的草稿；系统管理员也不例外。需同时持有“查看回收单”。', prerequisites=('view_recovery',)),
    _op('approve_recovery', '审批回收单', 'recovery', '回收', '需同时持有“查看回收单”；分公司行政只能审批本人创建的待审批单，行政组长及以上可审批当前数据范围内的待审批单，系统管理员可审批任意待审批单；审批后按重新入库或直接处置处理。', prerequisites=('view_recovery',)),

    _op('view_inventory', '查看盘点任务', 'inventory', '盘点', '查看当前数据范围内各状态任务、盘点流水和盘点报告及其导出。'),
    _op('edit_inventory', '编辑盘点', 'inventory', '盘点', '创建、维护、导入、重新盘点、删除和作废任务；可对异常项或全部清单重盘。需同时持有“查看盘点任务”；删除仅限待执行，作废限待执行/盘点中/已驳回。', prerequisites=('view_inventory',)),
    _op('review_inventory', '审批盘点任务', 'inventory', '盘点', '需同时持有“查看盘点任务”；分公司行政只能审批本人创建的待审批任务，行政组长及以上可审批当前数据范围内的待审批任务，系统管理员可审批任意待审批任务。', prerequisites=('view_inventory',)),

    _op('view_reconciliation', '查看对账', 'reports', '报表与对账', '查看当前数据范围内的对账任务和结果；列表、详情及导出要求同时持有“查看供应商字典”。', prerequisites=('view_suppliers',)),
    _op('manage_reconciliation', '维护对账', 'reports', '报表与对账', '按当前数据范围处理和归档对账；列表、详情、预览、导入、替换和差异处理均要求同时持有“查看对账”和“查看供应商字典”，导出仍由“查看对账”控制。', prerequisites=('view_reconciliation', 'view_suppliers')),
    _op('view_permission_matrix', '查看权限矩阵', 'permission_matrix', '权限矩阵', '只读查看全体员工的实际授权、岗位、组织归属和数据范围。'),
]

# Page and navigation access is kept beside the operation catalog so desktop
# and mobile entry points use the same permission relationships as assignment.
PAGE_ACCESS_OPERATIONS = {
    'dashboard': ['view_dashboard'],
    'reports': ['view_reports'],
    'categories': ['view_categories'],
    'asset_ledger': ['view_asset_ledger', 'import_asset_ledger', 'adjust_asset_ledger'],
    'instances': ['view_instances', 'edit_instances', 'change_instance_assignee'],
    'purchase': ['view_purchase'],
    'purchase_detail': ['view_purchase'],
    'assignment': ['view_assignment'],
    'assignment_detail': ['view_assignment'],
    'transfer': ['view_transfer'],
    'transfer_detail': ['view_transfer'],
    'recovery': ['view_recovery'],
    'recovery_detail': ['view_recovery'],
    'recovery_ledger': ['view_recovery_ledger'],
    'inventory': ['view_inventory'],
    'mobile_inventory': ['view_inventory'],
    'reconciliation': ['view_reconciliation'],
    'personnel': ['view_users', 'view_organizations'],
    'departments': ['view_departments'],
    'suppliers': ['view_suppliers'],
    'permission_matrix': ['view_permission_matrix'],
    'mobile_assets': ['view_asset_ledger'],
    'mobile_scan': ['view_asset_ledger', 'view_instances'],
    'mobile_my_documents': [
        'view_purchase', 'view_assignment', 'view_transfer', 'view_recovery',
    ],
    'mobile_approvals': [
        'approve_purchase', 'approve_assignment', 'approve_internal_transfer',
        'approve_recovery', 'review_inventory', 'view_purchase', 'view_assignment',
        'view_transfer', 'view_recovery', 'view_inventory',
    ],
    'mobile_approval_detail': [
        'approve_purchase', 'approve_assignment', 'approve_internal_transfer',
        'approve_recovery', 'review_inventory',
        'view_purchase', 'view_assignment', 'view_transfer', 'view_recovery', 'view_inventory',
    ],
    'mobile_notifications': ['view_notifications', 'view_approval_reports'],
}

_catalog_codes = {item['code'] for item in OPERATION_CATALOG}
_page_codes = {code for codes in PAGE_ACCESS_OPERATIONS.values() for code in codes}
if _page_codes - _catalog_codes:
    raise RuntimeError(f'Page access references unknown operation codes: {sorted(_page_codes - _catalog_codes)}')
_dependency_codes = {
    code
    for item in OPERATION_CATALOG
    for code in (
        item['prerequisites']
        + [conditional_code for codes in item['conditional_prerequisites'].values() for conditional_code in codes]
    )
}
if _dependency_codes - _catalog_codes:
    raise RuntimeError(f'Permission prerequisites reference unknown operation codes: {sorted(_dependency_codes - _catalog_codes)}')
if any(item['code'] in item['prerequisites'] for item in OPERATION_CATALOG):
    raise RuntimeError('An operation cannot require itself as a prerequisite')

# 旧码仅用于兼容和迁移核对；不作为可新授予的目录权限。
LEGACY_OPERATIONS = {
    'view_audit_logs': '查看审计日志（系统管理员专属，历史授权）',
    'view_audit': '查看审计日志（旧权限）',
    'manage_assets': '管理资产（旧权限）',
    'approve_transfer': '审批资产流转（旧权限）',
    'manage_dictionary': '管理字典（旧权限）',
    'adjust_ledger': '台账调整单（旧权限）',
    'manage_users': '管理用户（旧权限）',
    'manage_organizations': '管理组织架构（旧权限）',
    'approve_inventory': '审批盘点任务（旧权限）',
    'view_all_notifications': '查看抄送记录（旧权限）',
    'manage_instances': '管理固定资产实例（旧权限）',
    'manage_categories': '管理品目（旧权限）',
    'manage_departments': '维护部门字典（旧权限）',
    'manage_suppliers': '维护供应商字典（旧权限）',
    'dispose_assets': '处置回收物资（旧权限，需人工核对）',
    'create_categories': '新增品目（旧权限）',
    'delete_categories': '删除品目（旧权限）',
    'import_categories': '导入品目（旧权限）',
    'create_departments': '新增部门（旧权限）',
    'delete_departments': '删除部门（旧权限）',
    'create_suppliers': '新增供应商（旧权限）',
    'delete_suppliers': '删除供应商（旧权限）',
    'create_users': '新增员工账号（旧权限）',
    'delete_users': '删除员工账号（旧权限）',
    'create_organizations': '新增组织节点（旧权限）',
    'create_purchase': '创建采购入库单（旧权限）',
    'submit_purchase': '提交采购入库单（旧权限）',
    'withdraw_purchase': '撤回采购入库单（旧权限）',
    'import_purchase': '批量导入采购入库单（旧权限）',
    'create_assignment': '创建领用出库单（旧权限）',
    'submit_assignment': '提交领用出库单（旧权限）',
    'withdraw_assignment': '撤回领用出库单（旧权限）',
    'import_assignment': '批量导入领用出库单（旧权限）',
    'create_transfer': '创建调拨单（旧权限）',
    'submit_transfer': '提交调拨单（旧权限）',
    'withdraw_transfer': '撤回调拨单（旧权限）',
    'reject_transfer_inbound': '拒收调入调拨单（旧权限）',
    'import_transfer': '批量导入调拨单（旧权限）',
    'create_recovery': '创建回收单（旧权限）',
    'submit_recovery': '提交回收单（旧权限）',
    'withdraw_recovery': '撤回回收单（旧权限）',
    'create_inventory': '创建盘点任务（旧权限）',
    'manage_inventory': '维护盘点任务（旧权限）',
    'import_inventory': '导入盘点表（旧权限）',
    'rescan_inventory': '重新盘点任务（旧权限）',
    'view_inventory_report': '查看盘点报告（旧权限）',
    'view_return': '查看归还历史（已停用）',
    'create_return': '创建归还单（已停用）',
    'edit_return': '编辑归还单（已停用）',
    'delete_return_draft': '删除归还草稿（已停用）',
    'submit_return': '提交归还单（已停用）',
    'approve_return': '审批归还单（已停用）',
    'withdraw_return': '撤回归还单（已停用）',
}

OPERATIONS = {item['code']: item['label'] for item in OPERATION_CATALOG}

OPERATION_CHOICES = [(code, label) for code, label in OPERATIONS.items()]
OPERATION_PREREQUISITES = {
    item['code']: tuple(item['prerequisites'])
    for item in OPERATION_CATALOG
    if item['prerequisites']
}


def missing_operation_prerequisites(codes):
    selected = set(codes)
    return {
        code: tuple(prerequisite for prerequisite in OPERATION_PREREQUISITES.get(code, ())
                    if prerequisite not in selected)
        for code in selected
        if any(prerequisite not in selected
               for prerequisite in OPERATION_PREREQUISITES.get(code, ()))
    }


def is_valid_operation(code: str) -> bool:
    return code in _catalog_codes


def operation_by_code(code: str):
    return next((item for item in OPERATION_CATALOG if item['code'] == code), None)
