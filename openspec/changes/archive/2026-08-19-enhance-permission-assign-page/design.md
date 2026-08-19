## Context

`decouple-management-permissions` 已落地 `ManagementScope`（region/branch/team 三选一）+ `OperationGrant` 双维授权，`ScopeResolver` 支持 region→旗下分公司展开。`ManagementScope` 当前有 `exactly_one_org_node` CheckConstraint（region/branch/team 恰好一个非空）。前端 `views/admin/PermissionAssign.vue` 用原生 `<select>` 选员工、按节点类型（大区/分公司/行政组）添加授权。本变更新增"全部数据"授权、员工可搜索、大区覆盖范围可见。

约束：Django 5.1 + DRF；前端 Vue3 + Element Plus（项目已用）；`ManagementScope` 已有 CheckConstraint 与条件唯一约束需协同调整；`getUsers()`/`getBranches()` 已存在。

## Goals / Non-Goals

**Goals:**
- 新增"整个组织架构（全部数据）"授权类型，单条即覆盖全部组织（含未来新增节点）。
- 员工选择器支持按姓名 / 手机号搜索。
- 大区授权时及其在已授权列表中，可见其覆盖的分公司。

**Non-Goals:**
- 不改 `OperationGrant`（业务操作维度）。
- 不改 `ScopeResolver` 的 region→分公司展开逻辑（已实现），仅新增 `is_all_data` 分支。
- 不引入远程搜索（员工量级本地过滤即可；超大组织再迭代）。
- 不改授权的 CRUD 权限（仍仅 admin）。

## Decisions

### 决策 1：用 `is_all_data` 布尔字段表示"全部数据"授权
在 `ManagementScope` 新增 `is_all_data`（默认 False）。`is_all_data=True` 的行表示全局授权，region/branch/team 均为空。
**Why**：显式字段比"三节点全空=全部"的隐式约定更清晰、可读、可校验；与现有节点字段并列，改动最小。
**Alternatives**：①三节点全空约定为"全部" → 依赖隐式语义、易与校验疏漏冲突（否决）；②新增独立 `GlobalScope` 模型 → 多表、查询 union 复杂（否决）。

### 决策 2：调整 CheckConstraint 为"全部数据 或 恰好一个节点"
```
(is_all_data=True AND region/branch/team 全空)
OR (is_all_data=False AND region/branch/team 恰好一个非空)
```
新增条件唯一约束 `UniqueConstraint(fields=['user'], condition=Q(is_all_data=True), name='uniq_user_all_data')`，保证每用户至多一条全局授权。
**Why**：DB 层杜绝非法组合与重复全局授权。

### 决策 3：`ScopeResolver` 命中 `is_all_data` 即返回全部
在 admin 判断之后、节点收集之前增加：若该用户存在 `is_all_data=True` 的授权，直接返回 `Scope(all=True)`。
**Why**：与 admin 走同一"全部"出口，语义一致；一条全局授权即等价全部数据。

### 决策 4：序列化器校验互斥
`ManagementScopeSerializer.validate`：`is_all_data=True` 时 region/branch/team 必须全空；任一节点非空时 `is_all_data` 必须为 False（缺省）。模型层 `clean()` 同步该校验。
**Why**：双层（DRF + 模型）防御非法组合。

### 决策 5：员工选择器用 Element Plus `el-select filterable`
`PermissionAssign.vue` 的原生 `<select>` 改为 `<el-select :filterable="true">`，按 `name`/`phone` 过滤。复用已加载的 `users` 列表（`getUsers()` 返回全部，量级可本地过滤）。
**Why**：项目已全局引入 Element Plus，`filterable` 是其内置能力，零额外成本；比自建搜索框更一致。
**Alternatives**：原生 `<input>` + 手写过滤 → 增加状态与代码（否决）。

### 决策 6：大区覆盖分公司在 UI 双处可见
- **授予时**：节点类型选"大区"且选定某大区后，下方展示"含 N 个分公司：a、b、c"（由已加载的 `branches` 按 `region` 过滤）。
- **已授权列表**：大区类型的授权项展示为"大区：X（含 N 个分公司）"。
**Why**：让"授大区即含全部分公司"这一既定后端行为对管理员透明，避免误以为还需逐个分公司授权。

## Risks / Trade-offs

- **[CheckConstraint 迁移在 SQLite 的兼容]** → 条件约束 SQLite 3.8+ 支持，项目开发用 SQLite、生产 PostgreSQL，均满足；迁移仅 ADD COLUMN + ALTER 限制，无数据回填。
- **[is_all_data 与具体节点并存于同一用户]** → 由 CheckConstraint（行内）阻止单行组合；跨行的"既有全局又有节点"视为冗余但无害（全局已覆盖全部），不做额外阻止，仅文档说明。
- **[员工量大时本地过滤卡顿]** → 当前 `getUsers()` 全量返回、量级有限；若后续超千级，改为远程搜索（Non-Goal，留待迭代）。
- **[大区→分公司展示需 branches 已加载]** → 页面 `onMounted` 已 `getBranches()`，直接前端过滤，无需额外请求。
