## Context

磐盘的权限目前完全由 `User.role`（admin/manager/supervisor/leader/staff，数值越小越高）单字段驱动，三层硬编码实现：

1. **接口级**：`core/permissions.py` 的 `IsRoleMin`（读 ViewSet 的 `min_role` 比对等级）、`IsAdmin`、`CanApprove`（硬编码 `<= 3`）。
2. **数据级**：`DataScopeMixin`（`core/permissions.py:36-88`）按 `role + region/branch` 外键推导——admin/manager=全部，supervisor(有 region)=本大区，其他(有 branch)=本分公司；逻辑散落在 if/elif 字符串比较中，依赖目标模型恰好有 `branch`/`分公司`/`from_branch` 字段名（鸭子类型 + 中文 CharField 耦合），且异常被 `except: pass` 静默吞掉（存在越权降级风险）。
3. **无授权实体**：全后端无 Permission/Role/Scope 模型（仅 Django 内置 `groups`/`user_permissions` 未被自定义使用）。

组织层级为 `Region → (Branch, Team)`，Team 挂在 Region 下；`User` 同时冗余持有 `branch` + `region` 两 FK（无一致性约束）。痛点：行政主管（supervisor）同时管理自己的行政组时，范围只能由职位推导，无法精细/跨组织授权；`leader`（组长）数据范围与 staff 相同，看不到下属，名不副实。

约束：Django 5.1 + DRF；模型用中文字段名；UUID 主键；前后端 `ROLE_LEVELS` 同构（需手工同步）；生产已上线，需平滑迁移。

## Goals / Non-Goals

**Goals:**
- 将"职位"（`role`，组织归属）与"管理权限"（数据范围 + 业务操作）彻底解耦。
- 新增独立授权模型，支持**组织节点**（大区/分公司/行政组）与**业务操作**（模块/动作）两个维度的细粒度授权。
- `DataScopeMixin` 改为查询员工被授予的组织节点，消除角色推导与字段名耦合。
- 接口级权限改为基于业务操作授权判断。
- admin 走职位最高权限，不参与授权（安全兜底）。
- 提供数据迁移，保留所有现有用户的既有能力，平滑过渡。

**Non-Goals:**
- 不改组织架构模型本身（Region/Branch/Team 结构、Team 挂在 Region 下等保持现状）。
- 不引入运行时动态权限引擎或 ABAC 框架（用显式授权表 + 辅助方法即可）。
- 不做权限的层级继承（如"授大区自动可再分配给下属"）；授权即最终范围。
- 不调整认证机制（手机号 + ExpiringToken 不变）。
- 不在本变更内重做前端整个权限 UI 框架，仅新增"权限分配"页面与改造现有判断点。

## Decisions

### 决策 1：新建 `apps/permissions` app，承载授权模型
**Why**：授权是横切关注点，独立 app 便于复用与测试，不污染 `users`（归属）或各业务 app。
**Alternatives**：放进 `apps/users` → 与用户归属模型耦合，职责混杂（否决）；复用 Django 内置 `auth.Permission` → 自动生成的 CRUD perm 与"业务操作"语义不符，且中文化困难（否决，见决策 3）。

### 决策 2：组织节点授权用单表 + 三个可空 FK（`ManagementScope`）
模型：`ManagementScope(user, region?, branch?, team?)`，每行代表一个授权节点，三 FK 至多填一个层级：
- 填 `region` → 管理该大区（隐含旗下全部分公司/行政组）
- 填 `branch` → 管理该分公司
- 填 `team` → 管理该行政组

**Why**：单表易查询、易 union（一个员工可有多行=多授权），避免泛型外键（content_type）的复杂性与查询成本；三 FK 可空比"每节点一张 M2M 表"更聚合。
**Alternatives**：泛型外键（`content_type`+`object_id`）→ 灵活但查询难、丢失外键完整性（否决）；三张独立 M2M 表 → 分散，union 逻辑碎（否决）。

### 决策 3：业务操作授权用自定义 `OperationGrant(user, code)` + 操作码注册表
模型：`OperationGrant(user, code)`（code 为字符串操作码）。在 `apps/permissions/operations.py` 集中定义操作码注册表（初始集合，可扩展）：
- 审批类：`approve_purchase` / `approve_transfer` / `approve_inventory`
- 管理类：`manage_users` / `manage_organizations` / `manage_categories`
- 导入类：`import_assets` / `import_transfers`
- 报表：`view_reports`

提供 `user.can(code)` 辅助方法。**Why**：业务操作非 CRUD，自定义表语义清晰、完全可控、契合中文命名约定；操作码集中注册便于审计与前端枚举。
**Alternatives**：复用 Django `auth.Permission` + `user_permissions` → 免费得 `has_perm`，但 perm 码按模型自动生成、语义 muddy、与 DRF `DjangoModelPermissions` 耦合过深（否决）。

### 决策 4：`DataScopeMixin` 重构为"声明式字段映射 + ScopeResolver"
- 新增 `ScopeResolver`：给定 user，返回结构化范围 `{regions: [...], branches: [...], teams: [...]}`（展开 region→旗下 branch；admin 返回 `ALL` 哨兵）。
- `DataScopeMixin` 不再鸭子类型探测字段名，改为各 ViewSet 在类属性上**声明映射**（如 `scope_branch_field = '分公司'`、`scope_team_field = '所属行政组'`、`scope_transfer_fields = ('from_branch','to_branch')`），mixin 据此应用 `__in` 过滤；无授权且非 admin → 返回空查询集（或仅自身，按模型约定）。
**Why**：消除中文 CharField 字段名硬编码探测与异常静默吞掉，把脆弱的隐式约定变为显式声明。
**Alternatives**：保留鸭子类型仅换数据来源 → 字段名耦合与越权降级风险仍在（否决）。

### 决策 5：接口级权限改 `OperationPermission`，ViewSet 声明所需操作码
- 新增 `OperationPermission`，读 ViewSet 类属性 `required_operation`（或按 action 细分 `required_operations = {'approve': 'approve_transfer'}`）。
- `user.can(code)` 或 admin 即放行；移除 `IsRoleMin` / `min_role` / `CanApprove` 的角色等级硬编码。
**Why**：接口权限与业务操作对齐，而非职位等级。

### 决策 6：admin 兜底
`role == 'admin'` 在 `ScopeResolver`（返回 ALL）与 `user.can()`（恒真）中短路，永不查授权表。**Why**：避免误删/误配置导致系统锁死，符合"admin 不走授权"的决策。

### 决策 7：`role` 字段保留为纯归属 + admin 标识
`User.role` 不删除：继续表示职位/组织归属与展示；权限层除 admin 判断外不再读取它。`ROLE_LEVELS` 前后端保留（用于排序/展示），但不再驱动权限。**Why**：最小改动、保留展示语义、不破坏现有数据。

## Risks / Trade-offs

- **[迁移遗漏导致既有用户丢能力]** → 数据迁移按"重现旧有效范围"种子授权（见下），并为迁移写专项测试覆盖每类角色。
- **[leader 现状是"本分公司"，迁移后若按 team 授权会收窄]** → 迁移策略对 leader/staff 一律按 `branch` 授其所在分公司（重现旧范围），不擅自收窄；收窄交由管理员后续手动调整。
- **[授权表膨胀 / 查询性能]** → `ScopeResolver` 结果在单次请求内缓存（per-request memoize）；授权表对 `(user, region/branch/team)` 与 `(user, code)` 建索引。
- **[声明式字段映射需逐 ViewSet 改造]** → 改造范围大、易遗漏 → tasks 中按 app 逐一列出，并以"全站无残留 min_role / 旧 DataScope 逻辑"为验收点。
- **[manager 旧为"全部"、新模型下不再隐含]** → 迁移为现有 manager 种子"全部大区"授权以保留能力；文档注明 manager 此后需显式授权。
- **[越权降级风险（旧 except: pass）]** → 重构后无授权返回空集而非放行；ScopeResolver 异常显式上报，不静默降级。

## Migration Plan

1. **新增模型与 app**：建 `apps/permissions`（`ManagementScope`、`OperationGrant`、`operations.py` 注册表），`makemigrations`。
2. **新增权限层**：`ScopeResolver`、`OperationPermission`、`user.can()`，与旧实现并存（未切换）。
3. **数据迁移种子授权**（`RunPython`，按旧有效范围）：
   - `admin` → 不种子（走兜底）。
   - `manager` → 为其种子"全部 active Region"的 `ManagementScope`（保留"全部"能力）+ 全部操作码（保留原隐含的管理/审批能力）。
   - `supervisor`(有 region) → 种子 `ManagementScope(region=其region)` + 原 supervisor 隐含的操作码（审批/管理类）。
   - `leader`/`staff`(有 branch) → 种子 `ManagementScope(branch=其branch)`。
   - 无 region/branch 的非 admin → 不种子（旧逻辑下本就"不过滤"，但为安全收窄为空；记录日志供人工核查）。
4. **切换 ViewSet**：逐 app 把 `min_role`/`CanApprove` 换为 `required_operation`，把 `DataScopeMixin` 升级为声明式 + `ScopeResolver`。
5. **回归**：每类角色登录验证数据范围与操作能力与迁移前一致；行政主管新增"仅管理某行政组"授权后范围正确收窄。
6. **回滚**：迁移为纯新增（不改/不删旧字段），回滚即下线新 app 与切换点、恢复旧 `DataScopeMixin` 逻辑分支；授权表数据可保留不碍事。

## Open Questions

- **操作码初始集合**是否覆盖全部现有 `min_role`/`CanApprove` 场景？需在 tasks 阶段逐一核对各 ViewSet 的 `min_role` 赋值（audit=admin、categories 写=supervisor、users 默认=supervisor、assets 写/导入=supervisor、notifications manager 等），映射到操作码。
- **"无授权非 admin 用户"对自身数据**（如查自己的资产）如何处理？倾向：资产/流转类按"自身相关"返回（创建人/使用人为本人的），用户类返回自己——需在声明式映射中区分"管理范围"与"个人范围"。
- **是否需要"权限模板/角色组"**批量授权（如一键授"分公司管理员"套餐）？本变更不做，作为后续增强。
