## 1. 修复"创建盘点任务"按钮不可见

- [ ] 1.1 检查 `InventoryTaskList.vue` 中 `.btn-primary` 样式，确保文字和背景色对比度足够
- [ ] 1.2 在浏览器 DevTools 中确认按钮实际渲染状态，排除 CSS 变量未定义的情况

## 2. 添加分公司筛选下拉

- [ ] 2.1 在 `InventoryTaskList.vue` 筛选区（`filter-row`）中添加分公司 `<select>` 下拉，使用 `branchOptions` prop
- [ ] 2.2 下拉变更时 emit `update:filters` 更新 `filters.branch` 字段
- [ ] 2.3 确认 `Inventory.vue` 父组件的 `fetchTasks` 方法已使用 `filters.branch` 参数

## 3. 验证

- [ ] 3.1 本地构建确认无 TS 错误
- [ ] 3.2 部署到服务器并在浏览器中验证按钮可见、分公司筛选可用
