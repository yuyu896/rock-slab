## 1. 删除人员管理标签页

- [x] 1.1 在 `Organization.vue` 中删除 `activeTab` 的 `personnel` 选项
- [x] 1.2 删除标签页导航中的"人员管理"标签按钮
- [x] 1.3 删除 `personnel` 标签页的模板内容（表格、筛选器、分页等）
- [x] 1.4 删除 `personnel` 相关的 ref 变量（personnelKeyword、personnelRoleFilter、personnelRegionFilter、personnelBranchFilter、personnelTeamFilter、personnelStatusFilter、personnelList）
- [x] 1.5 删除 `fetchPersonnelList` 函数

## 2. 删除折叠/展开按钮

- [x] 2.1 删除侧边栏工具栏中的"折叠架构"按钮
- [x] 2.2 删除侧边栏工具栏中的"展开架构"按钮
- [x] 2.3 删除 `collapseAll` 和 `expandAll` 函数（如果没有其他地方使用）

## 3. 添加节点操作按钮

- [x] 3.1 在人员节点详情面板中添加"编辑"按钮，点击调用 `editItem(user, 'users')`
- [x] 3.2 在人员节点详情面板中添加"删除"按钮，点击调用 `deleteUserItem(user)`
- [x] 3.3 在区域节点详情面板中添加"编辑"按钮 — 无区域详情面板，不适用
- [x] 3.4 在行政组节点详情面板中添加"编辑"按钮，点击调用 `editItem(team, 'team')`
- [x] 3.5 在行政组节点详情面板中添加"删除"按钮，点击调用 `deleteTeamItem(team)`（需新增此函数）

## 4. 新增删除行政组函数

- [x] 4.1 新增 `deleteTeamItem` 函数，调用 `deleteTeam` API 并刷新数据

## 5. 验证

- [x] 5.1 确认人员管理标签页已删除，页面仅显示三个标签页
- [x] 5.2 确认侧边栏无折叠/展开全部按钮
- [x] 5.3 确认选中人员节点时，详情面板显示编辑和删除按钮
- [x] 5.4 确认选中行政组节点时，详情面板显示编辑和删除按钮
- [x] 5.5 确认编辑/删除功能正常工作
