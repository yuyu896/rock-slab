## Context

当前组织架构模块有三个标签页：组织架构、区域管理、分公司管理。后端 `/api/teams/` 已提供行政组的完整 CRUD API，但前端没有对应的标签页来管理行政组。侧边栏组织架构树的 `buildOrgTree` 函数只处理了有归属的员工（按 region/team 匹配），没有 team 且没有 region 的在职员工不会出现在树中。

## Goals / Non-Goals

**Goals:**
- 新增行政组管理标签页，支持行政组的列表展示和 CRUD
- 在侧边栏树中显示未归属人员

**Non-Goals:**
- 不修改后端 API
- 不改变侧边栏树的层级结构（行政经理→区域→主管→行政组→成员）

## Decisions

**1. 行政组标签页使用卡片网格布局**

与区域管理一致，使用 `.region-grid` 相同的卡片布局展示行政组。每个卡片显示：组名、所属区域、组长、组员数量、状态开关、编辑/删除按钮。新增按钮复用 `.btn-add` 样式。

**2. 未归属人员作为树底部独立分组**

在 `buildOrgTree` 的末尾，筛选出没有 `team` 和 `region` 归属的在职员工（排除 manager 角色，因为 manager 已作为顶层节点），作为一个"未归属人员"虚拟节点添加到树顶层。节点 ID 使用 `unassigned` 前缀。

筛选条件：`u.status === 'active' && !u.team && !u.region && u.role !== 'manager'`

**3. `activeTab` 类型扩展**

从 `'orgchart' | 'regions' | 'branches'` 扩展为 `'orgchart' | 'regions' | 'branches' | 'teams'`。

## Risks / Trade-offs

- 未归属人员节点是虚拟节点，不可编辑/删除，只能点击查看人员详情 → 可接受
- 行政组标签页的表单复用现有 `editingItem` + `showModal` 机制，与人员/区域表单共用弹窗 → 已有 `type === 'team'` 分支
