## Why

员工只能挂分公司（`User.branch`），但业务上有些员工长期归属某个行政组、不隶属任何分公司（如物资管理岗）。这类员工当前 `branch` 为空，系统默认数据范围是空集，导致他们在组织架构树中除集团根节点外不可见，且无法操作任何业务单据。

## What Changes

- `User` 模型新增 `team` 可空外键（→ `Team`），允许员工直接归属行政组而不必挂分公司
- **约束**：`branch` 有值时 `team` 强制为 null（区域/行政组由 `branch.team` 派生，不冗余存储）；`branch` 为空时 `team` 可单独赋值
- 默认数据范围兜底：`branch` 为空且 `team` 有值时，范围回退到该行政组下所有分公司
- 组织架构树行政组节点，直属 `team` 员工纳入员工列表
- 新增/编辑/移动员工表单支持设置所属行政组（`branch` 为空时）
- 移动员工弹窗支持选择"仅归属行政组"（无分公司）

## Capabilities

### New Capabilities

- `user-team-affiliation`: 员工直接归属行政组的数据模型、后端范围推导、前端表单与树展示

### Modified Capabilities

- `unified-organization-page`: 移动员工弹窗支持"仅行政组"目标；组织树行政组节点员工过滤规则扩展为包含 `u.team === team.id` 的直属员工
- `personnel-management`: 员工创建/编辑表单新增"所属行政组"字段（`branch` 有值时只读派生展示，`branch` 为空时可选）

## Impact

- **后端模型**：`apps/users/models.py`，新增 `team` FK + migration
- **后端序列化**：`apps/users/serializers.py`，回填 `teamName`；写入时验证 branch/team 互斥约束
- **后端过滤**：`apps/users/filters.py`，支持按 `team` 过滤
- **后端数据范围**：`apps/permissions/scope.py`，`branch` 为空时 team 下分公司兜底
- **后端用户视图**：`apps/users/views.py`，`_get_user_queryset` 和 `_validate_in_scope` 支持 team 路径
- **前端类型**：`frontend/src/types/index.ts`，`User` 加 `team?: string | null`
- **前端工具函数**：`frontend/src/utils/orgTree.ts`，`filterEmployeesByNode` team 节点纳入 `u.team` 员工
- **前端组织架构页**：`frontend/src/views/Organization.vue`，表单和移动弹窗调整
