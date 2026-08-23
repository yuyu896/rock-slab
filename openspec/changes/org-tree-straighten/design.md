## Context

现网数据形态（本地库实测）：2 个分公司 team 均为空、0 个员工挂分公司（13 用户中 6 有 region、4 有 team、5 有 leader——全部是平铺 FK）。生产库结构相同、量级相近（小规模）。既有迁移前科：SQLite 测试全绿、生产 PG 爆炸（数据库特定聚合），本轮迁移全程纯 Python 循环。

涉及历史包袱：`assign_branch_team_from_employees` 管理命令（员工众数回填，仅回填 team 为空的分公司）、`unified-organization-page` 基线中的「未分组」节点与三级级联移动、permissions 应用 0002 迁移曾按 `user.region` 种子授权（已执行过，不改写历史）。

## Goals / Non-Goals

**Goals:**
- 模型与现实一致：每个节点恰有一个父级；`Branch.team` 必填，`Branch.region`/`User.region`/`User.team`/`User.leader` 删除；
- 迁移可重复执行于 SQLite（开发/测试）与 PostgreSQL（生产），无信号数据有确定兜底；
- 权限范围沿树展开，既有授权（region/branch/team 节点）语义不丢；
- 组织页无「未分组」假节点，负责人在其节点可见。

**Non-Goals:**
- 不动 `ManagementScope`/`OperationGrant` 模型与授权 UI（小案③）；
- 不处理 supervisor 退役、岗位模板；
- 不清理 `org-teams-tab` 等旧基线 spec 的历史矛盾；
- 不做「按树自动推导用户权限」（任命即授权是 ③）。

## Decisions

### D1 Branch.team 必填 + PROTECT，region 归属派生

`team = FK(Team, on_delete=PROTECT, null=False, related_name='branches')`。选 PROTECT 而非 CASCADE：删组不应连坐删分公司；视图层捕获 ProtectedError 返回 400「该行政组下存在分公司」（与区域删除既有行为一致）。区域归属 = `branch.team.region`，serializer 以只读字段 `region` 暴露，旧消费方（权限分配页按区域筛分公司、组织页级联）零改动兼容——派生值不违反「只存一处」铁律。

### D2 回填策略：员工众数优先，区域兜底组收口

迁移内纯 Python：对 team 为空的分公司，先取其员工 team 众数（原管理命令逻辑并入）；无信号的分公司挂到其区域的「{区域名}未分组」行政组（get_or_create by name+region）。兜底组用真实 Team 而非虚拟节点——管理员后续可在组织页直接改名/重组，数据天然可见。回填完成后再 `AlterField(team, null=False)`，顺序由同一迁移内操作序列保证。

### D3 User 只留 branch；负责人可见性由树推导

删 `User.region/team/leader`。节点员工范围新规则（前端与后端 `_get_user_queryset` 同口径）：

- 分公司节点：`u.branch = 该分公司` ∪ `u = branch.manager`
- 行政组节点：`u.branch ∈ 组内分公司` ∪ `u = team.leader`
- 区域节点：`u.branch ∈ 区域旗下分公司（经行政组）` ∪ `u = region.manager` ∪ `u ∈ 该区域各组 leader`

负责人（manager/leader FK）保留在树节点上（③ 的「任命即授权」将消费它们），无 branch 的区长/组长凭此在其节点可见，替代原 `u.region` 平铺判断。

### D4 DataScope 树遍历：一切展开为分公司集合

`resolve_user_scope`：region 授权 → `Branch.objects.filter(team__region_id__in=regions)`；team 授权 → `Branch.objects.filter(team_id__in=teams)`；全部并入 `scope.branches`。`Scope.regions/teams` 仅作展示保留。`DataScopeMixin` 的 `scope_team_field` 死代码删除（无 ViewSet 使用）。用户列表 `Q(region__in=...)` 删除、`_validate_in_scope` 只查 branch。

### D5 移动/编辑员工只写 branch

前端移动弹窗保留 区域→行政组→分公司 级联（导航便利），删「未分组」选项；提交只带 `branch`。员工表单删区域/行政组下拉。「所属组织」列由 branch 派生（`branches.find(b => b.id === u.branch).team`）。

### D6 迁移顺序与依赖

`organizations.0007_backfill_team_and_drop_branch_region`：RunPython 回填（读历史 User.team，跨 app 取 historical model）→ AlterField(team 非空 PROTECT) → RemoveField(branch.region)。`users.0006_drop_flat_org_fks`：RemoveField ×3（region/leader/team）。users.0006 不依赖 organizations.0007 的结构变化（删列互相独立），但回填需要 User.team 仍存在——它在 organizations.0007 的 RunPython 里以 historical model 读取，只要 users.0006 尚未执行即可；用 `dependencies` 强制 organizations.0007 先于 users.0006（swappable_dependency 链上 users 依赖已存在，显式加 `('users', '0005_alter_user_role')` 并让 users.0006 depend on ('organizations','0007')）。

## Risks / Trade-offs

- [生产存在员工 team 与分公司实际归属不符的脏数据 → 众数回填错挂] → 兜底组集中暴露（「未分组」命名醒目），管理员在组织页可见可改；迁移输出回填清单日志。
- [删 User.region 后，无 branch 无任何挂靠的员工在树中不可见（仅集团根/搜索可见）] → 与设计 #12「User 只挂分公司」一致；此类多为行政/管理员账号，集团根可见。
- [PROTECT 改变删组行为（原为置空成员后删除）] → 有分公司的组删除被拒并提示，防误删；无分公司的组照常可删。
- [fresh 安装跑全量迁移] → permissions 0002 种子迁移读 `user.region_id`（historical），仍在 users.0006 之前执行，顺序由依赖保证。
- [前端四个死代码子页被误删] → 已验证无任何 import/路由引用；git 可恢复。

## Migration Plan

1. 全量备份（生产 PG）；
2. 部署迁移（回填 → 约束 → 删列）；迁移日志输出回填清单供人工核对；
3. 前端随同发布；组织页验收：无未分组节点、层级 集团→区域→行政组→分公司；
4. 回滚：revert 提交 + 恢复备份（删列迁移不做可逆数据恢复，靠备份）。

## Open Questions

无——层级结构与「未分组」兜底命名已在探索期与设计书定案；若用户对兜底组命名有偏好（如「默认组」），迁移后管理员可直接改名，不阻塞。
