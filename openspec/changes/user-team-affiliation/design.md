## Context

当前 `User` 模型只有 `branch`（nullable FK → Branch）一个组织归属字段。组织层级是集团 → 大区 → 行政组 → 分公司，员工的大区/行政组归属全部由 `branch.team.region` 派生。这对"长期无分公司、直接归属行政组"的员工是结构性缺陷：`branch` 为空时默认数据范围是空集，员工在架构树中除集团根节点外不可见，也无法操作业务单据。

## Goals / Non-Goals

**Goals:**
- `User` 新增 `team` 可空外键，允许直接归属行政组
- branch/team 互斥约束：`branch` 有值时 `team` 强制为 null，不冗余存储
- 默认数据范围兜底：`branch` 空且 `team` 有值时，范围 = `team` 下所有分公司
- 组织架构树行政组节点员工过滤纳入 `u.team` 员工
- 新增/编辑/移动员工表单支持设置所属行政组

**Non-Goals:**
- 不引入区域直属员工（`user.region` 字段），层级止于行政组
- 不改变分公司员工的任何现有逻辑
- 不改变权限授权模型（ManagementScope 不加 team 字段）

## Decisions

### D1：team 字段仅在 branch 为空时有业务意义

`branch` 有值时区域/行政组由 `branch.team.region` 派生，冗余存 `team` 会导致两套来源不一致。  
决定：后端 `UserSerializer.validate()` 或 `User.save()` 中，若 `branch` 非空则将 `team` 置 null。前端展示时，行政组从 `branch.teamName`（已有字段）或 `user.teamName`（新回填字段）读取。

### D2：scope 兜底用 team 下的分公司集合，而非 team_id 本身

`resolve_user_scope` 现在输出 `branches` 集合，下游所有范围判断（流转授权、用户可见性等）都消费 `scope.branches`，不感知 team。  
决定：在 `scope.py` 的默认兜底段（无显式授权时），`branch` 空且 `team` 有值时，将 `team` 下所有分公司 id 加入 `branches`，不改 `Scope` 数据结构。这样下游零改动。

### D3：`_validate_in_scope` 的 team 路径

`users/views.py` 第 494 行当前是 `in_branch = bool(target_user.branch_id and target_user.branch_id in scope.branches)`，`branch` 为空时直接拒绝。  
决定：先看 `in_branch`，不满足时再看 `in_team`：即 `target_user.team_id` 对应的 `team` 是否在操作者的 `scope.teams` 或其 `scope.branches` 能覆盖该 team 的全部分公司。最简实现：若 `scope.all` 或 target 的 team 下分公司全在 `scope.branches` 中则通过。

### D4：前端员工过滤纳入 `u.team`

`orgTree.ts` 的 `filterEmployeesByNode` team 节点当前只考虑 `u.branch ∈ teamBranches ∪ branch.manager ∪ team.leader`。  
决定：追加 `u.team === node.rawId`，直属该行政组的员工直接可见。区域节点也需传递：纳入 `u.team ∈ regionTeamIds` 的员工。

### D5：移动员工弹窗支持"仅归属行政组"

现有弹窗只选分公司，清空分公司表示"移出所有组织"。  
决定：弹窗改为两段：先选"目标行政组（可选）"，再选"目标分公司（可选）"，两者可独立清空。提交时：分公司有值则 `branch=id, team=null`；分公司空但行政组有值则 `branch=null, team=id`；两者均空则 `branch=null, team=null`。

## Risks / Trade-offs

- **迁移后旧有 `scope` 缓存失效**：`user._mgmt_scope_cache` 是请求级缓存，不跨请求，无需清理。→ 无风险。
- **`team` 下分公司集合为空时范围仍为空集**：若某行政组尚未建任何分公司，直属该行政组的员工数据范围仍为空。→ 可接受，行政组下无分公司时该员工本也无业务可操作；文档注明。
- **`_validate_delete_scope` 只看 branch**：删除员工时检查操作者范围也是 `target.branch_id`，`branch` 为空的员工会被拒绝删除（除 admin 外）。→ D3 修复后同步修复此处。
- **`DataScopeMixin`（资产等 app）仍按分公司过滤**：直属行政组员工的资产可见范围 = team 下分公司资产，这符合业务预期，无需改 DataScopeMixin。

## Migration Plan

1. 后端加 `team` 字段 → `makemigrations` → migration 写 `atomic=False`（PG 加列 nullable 不需要，但遵循项目惯例）
2. 无存量数据需回填（新字段默认 null，所有现有员工 `team=null` 是正确初态）
3. 前端改动无需特殊迁移
4. 部署后通过组织架构页手动为相关员工设置 `team` 归属

## Open Questions

- 无
