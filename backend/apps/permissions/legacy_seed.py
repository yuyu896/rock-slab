"""旧 role 模型 → 管理授权 种子逻辑。

从 0002 数据迁移中抽出，便于：
  - 迁移执行（传入 historical apps）
  - 单元测试直接调用（传入 None，使用当前 app registry）
"""
import logging

logger = logging.getLogger('permissions_migration')

# 旧 supervisor（level<=3）隐含的操作
SUPERVISOR_OPERATIONS = [
    'manage_users',
    'manage_categories',
    'manage_assets',
    'approve_transfer',
    'approve_inventory',
]
# 旧 manager（level<=2）在 supervisor 之上额外拥有
MANAGER_OPERATIONS = SUPERVISOR_OPERATIONS + [
    'view_all_notifications',
    'view_reports',
]


def _get_apps(apps):
    if apps is None:
        from django.apps import apps as apps_registry
        apps = apps_registry
    return (
        apps.get_model('users', 'User'),
        apps.get_model('organizations', 'Region'),
        apps.get_model('permissions', 'ManagementScope'),
        apps.get_model('permissions', 'OperationGrant'),
    )


def seed_legacy_grants(apps=None):
    """按旧 role + region/branch 为现有员工种子管理授权（保留既有能力）。"""
    User, Region, ManagementScope, OperationGrant = _get_apps(apps)

    unscoped_non_admin = []

    for user in User.objects.exclude(role='admin'):
        role = user.role
        region_id = getattr(user, 'region_id', None)
        branch_id = getattr(user, 'branch_id', None)

        if role == 'manager':
            region_ids = list(
                Region.objects.filter(status='active').values_list('id', flat=True)
            )
            ManagementScope.objects.bulk_create(
                [ManagementScope(user=user, region_id=rid) for rid in region_ids],
                ignore_conflicts=True,
            )
            _grant_operations(OperationGrant, user, MANAGER_OPERATIONS)
        elif role == 'supervisor' and region_id:
            ManagementScope.objects.get_or_create(user=user, region_id=region_id)
            _grant_operations(OperationGrant, user, SUPERVISOR_OPERATIONS)
        elif role in ('leader', 'staff') and branch_id:
            ManagementScope.objects.get_or_create(user=user, branch_id=branch_id)
        else:
            unscoped_non_admin.append((str(user.id), role))

    if unscoped_non_admin:
        logger.warning(
            '权限迁移：以下非 admin 用户无 region/branch，未种子授权，请人工核查：%s',
            unscoped_non_admin,
        )


def _grant_operations(OperationGrant, user, codes):
    OperationGrant.objects.bulk_create(
        [OperationGrant(user=user, code=c) for c in codes],
        ignore_conflicts=True,
    )


def reverse_legacy_grants(apps=None):
    """回滚：清空迁移种子出的授权数据。"""
    _, _, ManagementScope, OperationGrant = _get_apps(apps)
    ManagementScope.objects.all().delete()
    OperationGrant.objects.all().delete()
