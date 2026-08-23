## Context

小案②已完成组织树唯一父级（区域→行政组→分公司→员工），`resolve_user_scope` 现按 ManagementScope 沿树展开为分公司集合。运行时 role 残留依赖：通知路由按 role 列表筛人、移动端审批按钮 `hasMinRole('supervisor')`、用户岗位分配权 `MANAGEABLE_ROLES`；`IsRoleMin`/`CanApprove` 已无引用。本地库岗位分布：admin 2 / manager 4 / leader 2 / staff 3 / supervisor 2（生产量级相近，supervisor 无真人对应）。

## Goals / Non-Goals

**Goals:**
- 任命（树负责人字段）即授权：一次任命，范围即时生效；
- 岗位只做模板预填，运行时鉴权单一事实源 = 授权表（+admin 恒真）；
- supervisor 退役且存量可平滑换岗（逐人 diff 确认）；
- 权限可见性：矩阵页 + 生效权限卡，分配流程收敛为一页三步。

**Non-Goals:**
- 不动 ManagementScope/OperationGrant 模型与存量授权数据；
- 不做审批码按单据类型细分、新操作码执行点接入（P1/P2）；
- 不改登录认证与角色字段存储格式（role 字段继续存岗位标识）。

## Decisions

### D1 任命即授权的展开规则

`resolve_user_scope` 在既有 ManagementScope 展开之上并入任命：

```
region_ids  = Region.objects.filter(manager=user)          # 大区负责人
team_ids    = Team.objects.filter(leader=user)              # 行政组长
branch_ids  = Branch.objects.filter(manager=user)           # 分公司负责人
# 与授权节点同类展开：region→team→branch、team→branch，全部并入 scope.branches
```

任命是「身份」不是「记录」：不落 ManagementScope 表，实时计算（数量级小，无性能顾虑）；`Scope` 增 `appointed_regions/appointed_teams/appointed_branches` 集合仅供展示。一人可兼多职（如组长兼分公司负责人），范围取并集。

### D2 岗位模板注册表（后端单一事实源）

`apps/permissions/positions.py`：

```python
POSITION_TEMPLATES = {
    'admin':    {'label': '系统管理员', 'scope_type': 'all',     'operations': None},  # None=全部，运行时恒真
    'director': {'label': '大区负责人', 'scope_type': 'region',  'operations': [manage_users, manage_organizations, manage_categories, manage_assets, approve_transfer, approve_inventory, view_all_notifications, view_reports]},
    'manager':  {'label': '分公司负责人', 'scope_type': 'branch', 'operations': [manage_users, manage_categories, manage_assets, approve_transfer, approve_inventory]},
    'leader':   {'label': '行政组长',   'scope_type': 'team',    'operations': []},
    'staff':    {'label': '分公司行政',  'scope_type': 'branch', 'operations': []},
}
```

操作码集合沿用 legacy seed 语义（director=原 manager 集、manager=原 supervisor 集），无凭空新增能力。模板**仅预填**：分配页据此勾选，保存写 OperationGrant；后续单独增删不回写模板。`GET /api/permissions/position-templates` 返回模板（含全部操作码目录）。

### D3 supervisor 退役的三层处理

1. 岗位目录/下拉不再提供 supervisor；`User.ROLE_CHOICES` 删除该值（存量读不校验不炸，写接口拒新值）；
2. `MANAGEABLE_ROLES` 改岗位语义：admin 全部、director→[manager,leader,staff]、manager→[leader,staff]、leader→[staff]；
3. 存量换岗走 `migrate_positions`（见 D5），默认映射 supervisor→manager；前端 ROLE_LABELS 保留 supervisor 标签兼容未迁移展示。

### D4 通知路由与移动端按钮去角色化

- `get_approvers_for_branch`：候选 = `Q(operation_grants__code='approve_transfer') | Q(role='admin')`，active、distinct，再按 scope 过滤——与运行时审批权限（OperationPermission 查 approve_transfer + admin 恒真）完全同口径；
- 审批通过抄送：原 role ∈ [manager, director] → 持 `view_all_notifications` 的**非 admin** 用户且范围内（admin 免打扰；「查看抄送记录」权限即抄送资格，语义自洽）；
- 移动端 `hasMinRole('supervisor')` → `userStore.can('approve_transfer')`。

### D5 migrate_positions：逐人 diff，只补不删

管理命令默认 dry-run，输出逐人清单：`岗位 old→new（是否变化）｜模板操作码补授 [codes]｜任命节点 [区域X 负责人…（若已设）]｜生效范围 N 个分公司`。`--apply` 执行：更新 role（仅 supervisor→manager 映射）、按模板补建缺失 OperationGrant（ignore_conflicts）、绝不删除既有授权。既有 ManagementScope 一律保留（降级为「额外授权」）。

### D6 分配页三步 + 矩阵页（Excel 式朴素）

- 分配页（/admin/permissions 重构）：步骤1 选人 → 步骤2 选岗位模板（操作码勾选按模板预填，可增删）→ 步骤3 任命节点（按模板 scope_type 提示节点类型，写对应组织 API 的 manager/leader 字段）；右侧常驻「实时权限预览」：生效范围（任命+额外授权展开的分公司数/全部）+ 持有操作码清单；页底「特例调整」区保留 ManagementScope/OperationGrant 手工增删（跨区兼管等）。
- 矩阵页（/admin/permission-matrix）：上表 = 岗位×操作码模板矩阵（只读，✔ 标记预填）；下表 = 用户生效权限卡（每行：姓名/岗位/任命节点/额外授权/生效范围/持有操作码），数据来自 `GET /api/permissions/effective`。
- `effective` API（admin）：全员一次返回 `{user, role, appointments:[{type,name}], extra_scopes:[…], operations:[codes], scope_summary:{all|branch_count}}`，纯派生只读。

### D7 scope 缓存与一致性

任命字段变更（组织页编辑负责人）即时生效——`resolve_user_scope` 的 `_mgmt_scope_cache` 为单请求缓存，无跨请求陈旧问题；`effective` API 每次实时计算。

## Risks / Trade-offs

- [任命即授权使既有用户范围扩大（如某区长此前只有部分授权）] → 行为变化即设计目的；`effective` API + 矩阵页使扩权可见；diff 清单标注任命带来的范围变化。
- [supervisor→manager 默认映射可能不合个别实际] → diff 默认 dry-run、逐人确认，--apply 前可人工先在用户页改岗位。
- [通知抄送范围变化（manager 不再默认收 CC 除非持 view_all_notifications）] → 模板中 director 持该码；manager 岗位模板本就不含（沿用原 supervisor 集），与现状角色集 [manager,director] 的差异在 diff 清单与验收说明中明示。
- [操作码新增但无执行点] → 目录先注册（P1 契约先行），分配页可授予；矩阵页可见。
- [前端角色标签变化（行政总监→大区负责人等）] → 纯文案， UserRoleType 不变。

## Migration Plan

1. 部署后端（无数据库迁移）+ 前端；
2. 服务器执行 `python manage.py migrate_positions`（dry-run）核对逐人清单；
3. 确认后 `--apply` 换岗补授；
4. 验收：矩阵页可见全员生效权限；区长/组长任命后范围即时生效。
回滚：revert 提交；补授的 OperationGrant 不自动回收（如需可按 diff 清单手工清理）。

## Open Questions

无——岗位映射、模板操作码集合、supervisor 默认去向均沿设计书与 legacy seed 语义；如用户对 supervisor→manager 默认映射有异议，dry-run 清单阶段可改。
