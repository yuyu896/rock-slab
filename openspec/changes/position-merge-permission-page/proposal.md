## Why

2026-08-27 验收定案（v2-revision-draft.md 修订 3.2/3.3，已入设计书修宪记录 #12 与第七节）：原 staff 岗位模板为空，违背"岗位定操作、特例才单独授予"口诀，验收 T03/T06 所需权限无模板来源；且一个分公司行政仅约 2 人，无区分"负责人/操作员"的必要。同时权限分配页存在静默清权缺陷——选岗位时勾选集被模板整体替换、保存按差量增删，单独授予的额外权限会在换岗保存时被清除，与 `migrate_positions` 命令"只补不删"原则相反。本案为拆案计划（v2-revision-draft.md §八）第 5 案。

## What Changes

- **岗位合并（修订 3.2）**：分公司负责人(manager)与分公司行政(staff)合并为一个岗位「**分公司行政**」，角色码保留 `manager`，模板（scope_type=branch）预填 8 操作码：`manage_users` / `manage_dictionary` / `manage_assets` / `approve_transfer` / `approve_inventory` / `adjust_ledger` / `manage_instances` / `view_reports`。
- **staff 岗位退役**：岗位模板、用户创建/编辑可选项、岗位分配权线均不再含 staff（与 supervisor 退役同构）；存量 staff 用户由 `migrate_positions` 命令换岗为 manager（`LEGACY_POSITION_MAP` 增 `staff→manager`，只补不删）。
- **权限分配页脏检查（修订 3.3）**：「保存岗位」可用条件 = 岗位变化 **或** 操作码勾选集与既有授权存在差集（现状仅岗位变化，操作码改动后无入口保存）。
- **权限分配页只补不删（修订 3.3）**：换岗选模板时勾选集 = 模板项 ∪ 既有授权（现状为整体替换）；既有授权中不属于新模板的默认保留，页面提示"将保留岗位外的既有授权 N 项"，显式取消勾选才删除。与 `migrate_positions` 命令原则统一。
- **前后端角色常量同步**：角色体系收敛为四岗 admin(L1) > director(L2) > manager(L3=分公司行政) > leader(L4)；supervisor/staff 标注已退役仅作存量展示；前端各处角色文案与本地映射统一（CLAUDE.md 角色说明同步）。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `position-appointment-permissions`: 岗位模板条目改为四岗（manager=分公司行政 8 操作码，删除 staff 模板）；岗位目录接口返回四岗；新增「staff 岗位退役」requirement（镜像 supervisor 退役条文）；换岗迁移工具映射表增 staff→manager；新增「权限分配页保存脏检查与只补不删」requirement。

## Impact

- **后端**：`apps/permissions/positions.py`（manager 模板 8 操作码、删 staff 模板、LEGACY_POSITION_MAP 增 staff）、`apps/users/models.py`（ROLE_CHOICES 去 staff、默认 role 改 manager + 配套 migration，仅 DDL）、`apps/users/views.py`（MANAGEABLE_ROLES 去 staff、默认岗位、删 leader 只能建 staff 死代码）、`apps/permissions/management/commands/check_seed_grants.py`（存量 staff/supervisor 提示换岗）、`core/management/commands/seed_data.py`（种子用户 staff→manager）。
- **前端**：`constants/index.ts`（ROLE_LABELS/ROLE_LEVELS 四岗化）、`views/admin/PermissionAssign.vue`（脏检查 + 只补不删 + 保留提示 + 默认岗位）、`views/Organization.vue`（员工表单岗位选项四岗、新员工默认 manager、删弹窗死 user 字段块）、`layouts/MainLayout.vue` 与 `views/mobile/Home.vue`/`Profile.vue`（本地角色映射统一引用 ROLE_LABELS）。
- **测试**：后端 `tests/test_position_permissions.py`（四岗目录、8 操作码模板、staff 创建 400、存量 staff 不炸、迁移命令 staff 映射）；conftest 存量 staff fixture 保留作未换岗回归；前端 `npm run build` 类型门禁 + vitest。
- **部署**：`migrate_positions --apply` 需在部署后于服务器手动执行一次（supervisor 退役先例同流程）；命令只补不删，ManagementScope 全保留。
- **兼容**：运行时鉴权只看 OperationGrant/ManagementScope 与 admin 身份，岗位合并不改变任何既有授权；staff 退役后存量 staff 用户按既有授权正常工作，直至换岗。
