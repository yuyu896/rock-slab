## Why

组织架构模块缺少行政组管理标签页，无法直接对行政组进行新增/编辑/删除操作。同时侧边栏组织架构树中，没有设置 team/region 归属的员工不会显示，导致部分员工"消失"在组织架构中。

## What Changes

- 新增"行政组管理"标签页（与区域管理、分公司管理同级），提供行政组的列表展示、新增、编辑、删除功能
- 侧边栏组织架构树底部增加"未归属人员"节点，展示没有设置 team 和 region 归属的在职员工
- `activeTab` 类型扩展，新增 `'teams'` 选项

## Capabilities

### New Capabilities

- `org-teams-tab`: 行政组管理标签页，展示行政组列表卡片（组名、所属区域、组长、组员数量、状态），支持新增/编辑/删除行政组

### Modified Capabilities

- `org-sidebar`: 侧边栏组织架构树增加"未归属人员"分组节点

## Impact

- `frontend/src/views/Organization.vue`：新增标签页按钮、标签页内容区域、`activeTab` 类型扩展、`buildOrgTree` 增加"未归属人员"节点逻辑
- 后端 API 无需变更（`/api/teams/` 已有完整 CRUD）
