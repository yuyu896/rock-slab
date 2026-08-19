## 1. 新增 `apps/permissions` app 与授权模型

- [x] 1.1 新建 `apps/permissions`（apps.py、models.py、admin.py、注册到 INSTALLED_APPS）
- [x] 1.2 定义 `ManagementScope` 模型：`user` FK、可空 `region`/`branch`/`team` 三 FK（至多填一个层级）、继承 `UUIDModel`+`TimestampedModel`、中文字段 verbose_name、`__str__`；CheckConstraint(三选一) + 条件唯一约束
- [x] 1.3 定义 `OperationGrant` 模型：`user` FK、`code` choices、唯一约束 `(user, code)`
- [x] 1.4 新建 `apps/permissions/operations.py`，集中定义 9 个操作码注册表 + 枚举校验
- [x] 1.5 `makemigrations permissions` 生成 0001_initial（含约束）

## 2. 新增权限层（与旧实现并存，暂不切换）

- [x] 2.1 实现 `ScopeResolver`（`scope.py`）：返回 `{regions, branches, teams}`（region 展开→旗下 branch；admin 返回 ALL）；单次请求内 memoize 缓存
- [x] 2.2 在 `User` 增加 `can(code)` 方法（admin 恒真、否则查 `OperationGrant`）
- [x] 2.3 新增 `OperationPermission`：读 `required_operation` / 按 action 的 `required_operations`，调 `user.can()` 或 admin 放行
- [x] 2.4 重构 `DataScopeMixin` 为声明式：`scope_branch_field` / `scope_transfer_fields` / `scope_team_field`；无授权非 admin → `queryset.none()`；不再静默降级

## 3. 数据迁移（种子授权，保留既有能力）

- [x] 3.1 `manager` → 种子全部 active Region 授权 + MANAGER_OPERATIONS 操作码
- [x] 3.2 `supervisor`(有 region) → 种子其 region 授权 + SUPERVISOR_OPERATIONS 操作码
- [x] 3.3 `leader`/`staff`(有 branch) → 种子其 branch 授权
- [x] 3.4 `admin` → 不种子；无 region/branch 的非 admin → 记录日志供人工核查
- [x] 3.5 迁移逻辑抽到 `legacy_seed.py` 供复用；`tests/test_permission_migration.py` 覆盖每类角色（3 用例通过）

## 4. 切换各 ViewSet 到新权限层

- [x] 4.1 核对并映射各 ViewSet 的 `min_role` → 操作码（assets→manage_assets / transfers→approve_transfer,manage_assets / inventories→approve_inventory / users→manage_users / categories→manage_categories / organizations→manage_organizations / audit→view_audit / ApprovalCC→view_all_notifications）
- [x] 4.2 各业务 app ViewSet 移除 `min_role`/`CanApprove`/`IsRoleMin`，改用 `OperationPermission`
- [x] 4.3 各业务 app ViewSet 升级 `DataScopeMixin` 声明（assets/固定资产/盘点→`scope_branch_field='branch'`；调拨→`scope_transfer_fields=('from_branch','to_branch')`）
- [x] 4.4 全局检索确认无残留 `min_role` / `CanApprove` / 旧鸭子类型逻辑（已校验为空）
- [x] 4.5 `core/permissions.py` 保留 `ROLE_LEVELS`（展示用）；`IsRoleMin`/`CanApprove`/`IsAdmin` 定义保留但已无引用（conftest 同步按旧 role 种子授权）
- [x] （额外）`users/views.py` 的 `_get_user_queryset` / `_validate_in_scope` 改为按授权范围判断

## 5. 新增管理授权接口

- [x] 5.1 `apps/permissions/views.py`：`ManagementScopeViewSet` / `OperationGrantViewSet`（仅 admin），`operation_catalog`、`my_permissions` 函数视图
- [x] 5.2 序列化器：`ManagementScopeSerializer`（三选一校验）、`OperationGrantSerializer`（带 label）、`UserPermissionSummarySerializer`
- [x] 5.3 路由 `/api/permissions/management-scopes`、`/operation-grants`、`/operations`、`/me` 注册（已冒烟验证）

## 6. 前端适配

- [x] 6.1 新增 `api/permissions.ts`（授权 CRUD + 操作目录 + 当前用户权限摘要）
- [x] 6.2 新增"管理权限分配"页面 `views/admin/PermissionAssign.vue`（选员工 → 勾选业务操作 + 添加/移除组织节点），仅 admin 可见
- [x] 6.3 `store/user.ts` 增加 `operations`/`can()`/`isAdmin`/`fetchMyPermissions`（登录与 fetchProfile 后拉取）；`hooks/usePermission.ts` 的 `canApprove`/`canManageUsers`/`canManageCategories`/`canManageAssets` 改为消费操作授权
- [x] 6.4 路由 `/admin/permissions`（`requiresAdmin` 守卫）+ SidebarNav 仅 admin 可见入口

## 7. 测试与回归验收

- [x] 7.1 后端 pytest：新增 `test_management_permissions.py`（12 例）+ `test_permission_migration.py`（3 例）覆盖范围/操作/admin 兜底/迁移；全量套件 291+ 通过（仅 5 例预存失败与本变更无关：auth snake_case、openpyxl `vertical='middle'`）
- [x] 7.2 回归：admin 全权；各职位经 conftest 种子后既有能力保留；授予单分支→范围收窄；跨组织授权并集（测试覆盖）
- [x] 7.3 安全验收：无授权非 admin 见空范围（`test_staff_without_grant_sees_nothing`）；范围计算无静默降级（重构后异常显式）
- [x] 7.4 前端 `npm run build` 通过（类型检查 + 构建 ✓）；权限分配页面已接入路由与导航
