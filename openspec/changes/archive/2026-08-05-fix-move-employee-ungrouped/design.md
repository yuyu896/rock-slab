## Context

`frontend/src/views/Organization.vue` 现状：

- 树：区域 → 行政组 → 分公司；`team=null` 的分公司聚合为「未分组」虚拟节点（`type='team'`, `rawId=''`），**丢失区域 id**。员工不进树。
- 员工列表 `employees` computed 按选中节点过滤：分公司（`u.branch`）、行政组（`u.branch ∈ 组分公司`）、区域（`u.region`）。未分组节点 `rawId=''` 三分支全部落空 → `return []`（**bug**）。
- 行政组分支只按 `u.branch` 匹配分公司，**漏了 `branch=null` 但 `team=该组` 的员工**（张三案例）。
- 移动弹窗 `moveState = { employee, region, branch }`，行政组仅作只读提示，无下拉。

数据模型（`unified-organization-page` 已建立：区域→行政组→分公司，`Branch.team` 可空）足够支撑，不改后端。`User.branch`/`team`/`region` 均 `null=True`。

## Goals / Non-Goals

**Goals:**
- 未分组节点员工可见、可移动。
- 行政组节点右侧列表含直属该组的无分公司员工（`branch=null && team=该组`）。
- 移动弹窗改为 区域→行政组→分公司 三级级联，分公司必选。

**Non-Goals:**
- 员工不进树（保持「树导航 + 右侧列表」模式）。
- 不改后端模型/API（移动复用 `updateUser`）。
- 不做批量移动、不做拖拽改层级。
- 不自动给 `team=null` 分公司分配行政组。
- 不专门处理 `branch/team/region` 全空的员工（仅搜索可见，本提案不强求处理）。

## Decisions

### D1. 未分组节点携带 regionId
**选择**：`TreeNode` 增加可选 `regionId` 字段；未分组节点 `regionId=<区域id>`，`rawId` 保留 `''`。
**理由**：员工过滤需要区域归属来定位「该区域 `team=null` 的分公司」。相比从节点 `key`（`ungrouped-${r.id}`）解析字符串，显式字段更可靠、类型安全。

### D2. 未分组员工过滤
**选择**：`employees`/`nodeCount` 增加分支——`node.type==='team' && !node.rawId` 时，取 `regionId` 下 `team=null` 分公司的员工。
**理由**：与现有「行政组节点取其下分公司员工」对称，只是分公司集合换成「该区域未分组的分公司」。

### D3. 行政组节点含直属组无分公司员工
**选择**：行政组节点的员工集合改为 `u.branch ∈ 该组分公司` **∪** `(u.team=该组 && !u.branch)`。
**理由**：员工按「最具体归属」呈现——`branch=null` 但有行政组的员工，其最具体归属就是该行政组，应在组节点可见。解决张三案例。
**区域节点**：现有 `u.region=该区域` 已覆盖该区域所有员工（含 `branch=null` 的），无需改。
**分公司节点**：`u.branch=该分公司`，不变。

### D4. 移动三级级联，分公司必选（用户取舍 A）
**选择**：`moveState` 增加 `team`，结构 `{ employee, region, team, branch }`。区域 → 行政组 → 分公司；**分公司必选**；选分公司后 `team`/`region` 跟随分公司（`confirmMove` 语义不变：`team=target.team`, `region=target.region`）。
**理由**：员工列表/树都按 `branch` 归类，若允许只选行政组（`branch=null`），员工会落到 D3 的「直属组无分公司」状态——虽可见，但归属不完整；要求选分公司保证归属明确。

### D5. 行政组下拉含未分组（取舍 B）
**选择**：移动弹窗行政组下拉除真实行政组外，含「未分组」选项（value=`''`）。选「未分组」时分公司下拉列该区域 `team=null` 的分公司；选真实行政组时列该组下分公司。
**理由**：支持双向移动——既能把员工移出未分组（选真实行政组），也能移到尚未分配行政组的分公司（选「未分组」），避免「必须先给分公司分组才能调人」的流程阻塞。真实行政组 id 为 UUID，与 `''` 无冲突。
**权衡**：「未分组」作为移动目标时目标分公司归属不完整（`team=null`），但提供灵活性。

### D6. 员工不进树
**选择**：保持现有「树导航 + 右侧列表」模式，员工作为右侧列表项呈现，不作为树节点。
**理由**：树用于组织层级导航，列表用于排序/批量操作/编辑入口，双面板职责清晰；避免树节点爆炸。

## Risks / Trade-offs

- **[联动遗漏导致脏选择]** → `watch` 切换 `region` 清 `team`+`branch`，切换 `team` 清 `branch`；测试覆盖。
- **[全无归属员工不可见]** → `branch/team/region` 全空的员工在任何节点都看不到，仅搜索可见。已知限制，本提案不处理。
- **[D5 无法移到未分组分公司]** → 先给目标分公司分配行政组再移动；流程约束，可接受。

## Migration Plan

仅前端改动。部署：`deploy.sh`（前端 build + nginx reload），无后端 migrate。回滚：`git revert` 前端提交。

## Open Questions

（无。A/B 均已定：A=分公司必选，B=行政组下拉含未分组。）
