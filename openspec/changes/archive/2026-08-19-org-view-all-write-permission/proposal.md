## Why

组织架构模块（区域 / 分公司 / 行政组 / 人员）目前是「**能改才能看**」：非 supervisor 用户连这些管理界面的标签页都看不到（标签 `v-if="canManageOrg"`，而 `canManageOrg = hasMinRole('supervisor')`），并且有一个 watch 会把非管理员**强制切回架构图**。这导致普通员工完全无法查看组织架构信息。

应拆分读写权限：**所有人可查看**，**有权限才能修改**。

## What Changes

- **查看全开**：4 个管理标签页（区域/分公司/行政组/人员）对所有登录用户可见（去掉 `v-if="canManageOrg"`）；去掉把非管理员切回架构图的 watch。
- **修改按操作授权**：各管理界面的「新增/编辑/删除」按钮按操作权限 gating——区域/分公司/行政组 → `canManageOrganizations`；人员 → `canManageUsers`。同时把原来 role 式的 `canManageOrg = hasMinRole('supervisor')` 换成更准确的 operation 式（权限解耦后应以操作授权为准）。
- **后端无需改动**：`list/retrieve` 本就对所有登录用户开放（`required_operations` 只 gate 写操作）；写操作已按 `manage_organizations`/`manage_users` 校验。

## Capabilities

### New Capabilities
- `org-view-all-write-permission`: 组织架构管理界面（区域/分公司/行政组/人员）所有人可查看；修改按 `manage_organizations`/`manage_users` 授权。

### Modified Capabilities
<!-- 无：现有 specs 中不含组织架构读写分离 capability。 -->

## Impact

- **前端** `Organization.vue`：标签可见性 + 修改按钮 gating（引入 `canManageOrganizations`/`canManageUsers`）。
- 无后端改动、无 DB 迁移。
