## 1. 扩展 activeTab 类型

- [x] 1.1 将 `activeTab` 的类型定义扩展为 `'orgchart' | 'regions' | 'branches' | 'teams' | 'personnel'`

## 2. 人员管理标签页 UI

- [x] 2.1 在标签栏中添加"人员管理"按钮，绑定 `activeTab = 'personnel'`
- [x] 2.2 在 `tab-actions` 中添加"新增人员"按钮（`activeTab === 'personnel'` 时显示）
- [x] 2.3 添加人员管理标签页内容区域：搜索框 + 筛选下拉框（角色、区域、状态） + 表格

## 3. 搜索和筛选逻辑

- [x] 3.1 添加 `personnelKeyword`、`personnelRoleFilter`、`personnelRegionFilter`、`personnelStatusFilter` 响应式变量
- [x] 3.2 添加 `filteredUsers` computed，根据关键字和筛选条件过滤 `users`

## 4. 人员表格

- [x] 4.1 实现人员表格渲染：姓名、手机号、角色、所属区域、所属分公司、直属上级、状态开关、操作按钮（编辑/删除）
- [x] 4.2 实现空状态提示（无人员时显示）
