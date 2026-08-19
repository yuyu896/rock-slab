## Why

分公司管理编辑分公司时的「负责人」下拉，目前按**角色**筛选（仅 admin/director/manager/supervisor/leader，即「行政组长以上」），且**不按分公司归属过滤**。导致两个问题：

1. 普通员工（staff）即使归属该分公司，也**不能被选为负责人**；
2. 下拉会**混入其他分公司**的人，可选范围与该分公司无关。

应改为：下拉只列「归属到该分公司」的**全部员工**（不限角色，含 staff）。

## What Changes

- 分公司编辑表单「负责人」下拉选项由 `users.filter(角色 in leader+)` 改为 `users.filter(u => u.branch === 当前分公司 id)`——该分公司全部归属员工、含普通员工、不限角色。
- 「负责人」改为**可选**：新增分公司时尚无归属人员，允许留空（创建后到人员管理分配成员，再回来指派负责人）；既有分公司从其成员中选。
- **仅改分公司负责人下拉**；区域负责人下拉不动。
- 所需数据（全角色用户 + `branch` 字段）已在前端 `users` 就绪，**无需后端改动**。

## Capabilities

### New Capabilities
- `branch-manager-dropdown`: 分公司「负责人」下拉的来源 = 该分公司的全部归属员工（不限角色），且负责人可选。

### Modified Capabilities
<!-- 无：现有 specs 中不含分公司负责人下拉 capability。 -->

## Impact

- **前端** `Organization.vue` 分公司表单「负责人」下拉过滤逻辑 + 改为可选。
- 无后端改动、无 DB 迁移。
