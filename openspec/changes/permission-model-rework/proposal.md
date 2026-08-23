## Why

权限现状三套并存且互不知晓：六级角色线（IsRoleMin/CanApprove 已死代码，但通知路由、移动端审批按钮、用户岗位分配权仍按 role 判断）、OperationGrant 9 个操作码、ManagementScope 节点授权。任命与授权脱钩——组织树上的负责人字段（Region.manager / Team.leader / Branch.manager）不参与范围计算，给区长授了权还要去授权页再授一遍；分配权限要跑四处。总设计书第七节定案：**岗位定操作、任命定范围、特例才单独授予**，本轮落地。

## What Changes

- **任命即授权（运行时）**：`resolve_user_scope` 把树负责人任命并入范围计算——被任命为区域负责人/行政组长/分公司负责人的用户，其数据范围自动含该节点子树，与 ManagementScope 授权取并集。
- **岗位 = 权限模板（仅预填，不参与运行时鉴权）**：后端新增岗位模板注册表（岗位 → 预填操作码集合 + 任命节点类型提示）：admin→系统管理员（运行时恒真）、director→大区负责人、manager→分公司负责人、leader→行政组长、staff→分公司行政。分配页选岗位时按模板预填操作码，保存仍写 OperationGrant 表；运行时 `can()` 只查表。
- **supervisor 退役**：岗位清单不再提供 supervisor；`MANAGEABLE_ROLES`（岗位分配权线）去掉 supervisor；存量 supervisor 用户由迁移工具换岗（默认映射 manager），未迁移的存量值不炸（展示层兼容）。
- **操作码 9 → 13**：注册 `manage_dictionary`（管理品目字典）、`manage_instances`（管理固定资产实例）、`adjust_ledger`（台账调整单）、`dispose_assets`（资产处置）——P1/P2 消费，先入目录可授予。审批码暂不细分（单据模型 P2 重构时再拆）。
- **通知路由去角色化**：审批人路由从「role ∈ [admin/director/manager/supervisor] 且范围内」改为「持 `approve_transfer` 授权（或 admin）且范围内」；审批通过抄送从「manager/director」改为「持 `view_all_notifications` 的非 admin 用户且范围内」。
- **分配页三步化重构**：选人 → 选岗位模板（预填操作码，可增删）→ 任命节点（写树负责人字段）+ 保存前后实时权限预览（生效范围 + 持有操作）；ManagementScope/OperationGrant 的单独授予保留在同一页「特例调整」区。
- **新增权限矩阵页**（/admin/permission-matrix，Excel 式）：岗位 × 操作码模板矩阵 + 用户生效权限卡（每人：岗位、任命节点、额外授权、生效范围、持有操作码）。
- **新增 API**：`GET /api/permissions/position-templates`（岗位模板目录）、`GET /api/permissions/effective`（全员生效权限总览，admin）；`/api/permissions/me` 扩展任命节点与生效范围摘要。
- **逐人 diff 迁移命令**：`migrate_positions`（默认 dry-run）输出逐人清单——岗位现值→目标岗位、模板操作码补授 diff、任命带来的范围变化；`--apply` 执行（存量授予保留，只补不删）。
- **清理死代码**：删除 `core/permissions.py` 的 `IsRoleMin` / `CanApprove`。

## Capabilities

### New Capabilities
- `position-appointment-permissions`: 岗位模板 + 任命即授权契约——岗位仅预填操作码、任命树节点即授子树范围、运行时鉴权只查授权表；含岗位目录与 supervisor 退役规则。
- `permission-matrix-view`: 权限矩阵页与用户生效权限卡——岗位×操作码模板矩阵、全员生效权限 Excel 式总览、分配页三步流程与实时预览。

### Modified Capabilities
- `management-permissions`: 「数据范围必须由管理授权决定」扩展为「管理授权 ∪ 树负责人任命」，区域/分公司/行政组负责人任命 MUST 展开为子树范围；审批通知路由改按操作授权。

## Impact

- **后端**：`apps/permissions/{operations,scope,views,serializers,urls}.py`（模板注册表、任命并入、新 API）、`apps/notifications/signals.py`（路由去角色化）、`apps/users/{models,views}.py`（岗位清单/分配权线去 supervisor）、`core/permissions.py`（删死代码）；新增管理命令 `apps/permissions/management/commands/migrate_positions.py`。无模型结构变更（ManagementScope/OperationGrant 不动）。
- **前端**：`views/admin/PermissionAssign.vue` 重构为三步、新增 `views/admin/PermissionMatrix.vue` + 路由/侧边栏、`constants/index.ts` 岗位标签（admin→系统管理员、director→大区负责人、manager→分公司负责人、leader→行政组长、staff→分公司行政）、移动端 `ApprovalList/ApprovalDetail` 的 canApprove 改查操作授权、`api/permissions.ts` 新接口。
- **测试**：test_management_permissions / test_notifications / test_rbac_matrix / test_users / test_data_scoping 增补任命即授权与操作码路由断言；conftest supervisor 夹具保留（模拟历史岗位用户）。
- **非目标**：ManagementScope/OperationGrant 模型结构与既有授权数据不动；审批码按单据类型细分（P2 单据重构时）；新操作码的执行点接入（P1/P2）；登录/Token 机制不动。
