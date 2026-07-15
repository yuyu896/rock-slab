## Context

- `Organization.vue`：4 个管理标签（区域/分公司/行政组/人员）`v-if="canManageOrg"`，`canManageOrg = hasMinRole('supervisor')`（role 式）；并有 `watch(canManageOrg)` 把非管理员在这些标签时切回 `orgchart`。
- 后端：`Region/Branch/Team/User` ViewSet 的 `required_operations` 只 gate 写（`manage_organizations`/`manage_users`），`list/retrieve` 无声明即对所有登录用户放行；人员列表按数据范围(scope)可见。
- `usePermission` 已暴露 `canManageOrganizations = can('manage_organizations')`、`canManageUsers = can('manage_users')`（operation 式，权限解耦后为准确来源）。

## Goals / Non-Goals

**Goals:**
- 所有人可查看组织架构管理界面（标签 + 数据）。
- 修改按操作授权：区域/分公司/行政组需 `manage_organizations`，人员需 `manage_users`。

**Non-Goals:**
- 不改后端（读取已全开、写已校验）。
- 不改数据范围（人员列表仍按 scope 可见，非全员可见所有分公司人员）。
- 不放开越权写（后端 403 兜底仍在）。

## Decisions

### 决策 1：标签全开 + 去切回 watch
- **做法**：去掉 4 个管理标签的 `v-if="canManageOrg"`；移除把非管理员切回 `orgchart` 的 `watch`。
- **理由**：查看对所有人开放。

### 决策 2：修改按钮按 operation 授权
- **做法**：区域/分公司/行政组的「新增/编辑/删除」改 `v-if="canManageOrganizations"`；人员的改 `v-if="canManageUsers"`；移除不再使用的 `canManageOrg`。
- **理由**：权限解耦后以 operation 为准（与后端写校验 `manage_organizations`/`manage_users` 一致），比 `hasMinRole('supervisor')` 更准确。

## Risks / Trade-offs

- **[普通员工看到人员仅为本人 scope]** 人员列表仍按数据范围 → **接受**，符合既有隔离；区域/分公司/行政组本就全开。
- **[用户以为能改但无按钮]** 无授权者看不到修改按钮 → **缓解**：界面无入口；后端 403 兜底防越权。

## Migration Plan

1. 前端：`Organization.vue` 标签可见性 + 修改按钮 gating。
2. 纯前端逻辑，**无 DB 迁移**；部署即生效。

## Open Questions

（暂无。）
