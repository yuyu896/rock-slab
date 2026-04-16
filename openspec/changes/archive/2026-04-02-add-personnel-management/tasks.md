## 1. 标签页导航扩展

- [x] 1.1 在 `Organization.vue` 的 `activeTab` 类型中新增 `'personnel'` 选项，默认值保持 `'orgchart'`
- [x] 1.2 在模板中新增"人员管理"标签按钮，放置在"分公司管理"标签之后
- [x] 1.3 在标签操作区新增条件按钮：当 `activeTab === 'personnel'` 时显示"新增人员"按钮

## 2. 人员列表表格

- [x] 2.1 新增 `v-else-if="activeTab === 'personnel'"` 的 `tab-content` 区块
- [x] 2.2 实现搜索栏：关键词输入框（绑定 `personnelKeyword`）
- [x] 2.3 实现筛选下拉框：角色选择、区域选择、分公司选择、状态选择（绑定对应 ref）
- [x] 2.4 实现数据表格，列包含：姓名、手机号、角色、所属区域、所属分公司、直属上级、状态（开关）、最后登录时间、操作（编辑/删除）
- [x] 2.5 实现空状态提示："暂无人员数据"

## 3. 数据获取与筛选

- [x] 3.1 新增 `fetchPersonnelList` 函数，调用 `getUsers` 并传入筛选参数（keyword, role, branch, status）
- [x] 3.2 搜索和筛选变更时触发数据刷新（watch 或 input 事件）
- [x] 3.3 在 `onMounted` 中补充 `fetchPersonnelList` 调用

## 4. 新增人员表单

- [x] 4.1 在弹窗模板中新增 `type === 'personnel'` 的表单区块，字段包含：姓名、手机号、角色、所属区域、所属分公司、直属上级、初始密码（默认 123456）
- [x] 4.2 在 `saveItem` 函数中补充 `type === 'personnel'` 分支，调用 `createUser`

## 5. 编辑人员

- [x] 5.1 在表格操作列绑定编辑按钮，调用 `editItem(user, 'personnel')`
- [x] 5.2 在 `saveItem` 函数中补充编辑分支，对 `type === 'personnel'` 调用 `updateUser`

## 6. 启停与删除

- [x] 6.1 表格状态列绑定 `toggleUserStatus`，切换 active/inactive
- [x] 6.2 表格操作列绑定删除按钮，调用 `deleteUserItem` 弹出确认后删除

## 7. 样式

- [x] 7.1 补充人员管理标签页的筛选栏样式（`.filter-bar`、`.filter-item`）
- [x] 7.2 确保表格在不同数据量下的样式一致性，复用已有 `.data-table` 样式
