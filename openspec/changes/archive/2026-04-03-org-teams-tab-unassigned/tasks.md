## 1. 扩展 activeTab 类型

- [x] 1.1 将 `activeTab` 的类型定义从 `'orgchart' | 'regions' | 'branches'` 扩展为 `'orgchart' | 'regions' | 'branches' | 'teams'`

## 2. 行政组标签页 UI

- [x] 2.1 在标签栏中添加"行政组"按钮，使用与其他标签一致的样式，绑定 `activeTab = 'teams'`
- [x] 2.2 添加"行政组"标签页内容区域，包含"新增行政组"按钮和卡片网格容器
- [x] 2.3 实现行政组卡片渲染：组名、所属区域、组长、组员数量、状态开关、编辑/删除按钮
- [x] 2.4 实现空状态提示（无行政组时显示）

## 3. 行政组 CRUD 逻辑

- [x] 3.1 添加 `teams` 响应式数据，在 `loadTeams` 中调用 `GET /api/teams/` 获取行政组列表
- [x] 3.2 实现新增行政组：打开表单弹窗（组名必填、所属区域必填、组长可选），调用 `POST /api/teams/`
- [x] 3.3 实现编辑行政组：预填当前数据的表单弹窗，调用 `PUT /api/teams/<id>`
- [x] 3.4 实现删除行政组：确认对话框后调用 `DELETE /api/teams/<id>`

## 4. 未归属人员节点

- [x] 4.1 在 `buildOrgTree` 函数末尾，筛选出 `status === 'active' && !team && !region && role !== 'manager'` 的员工
- [x] 4.2 为符合条件的员工创建"未归属人员"虚拟节点（ID 使用 `unassigned` 前缀），作为树顶层子节点

## 5. 行政组卡片样式

- [x] 5.1 添加行政组卡片样式，复用 `.region-grid` 布局和 `.region-card` 卡片基础样式
