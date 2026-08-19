## 1. 数据层改造

- [x] 1.1 在 SidebarNav.vue 中导入 `getInventoryTasks` API 和 `ref`、`computed`、`onMounted`
- [x] 1.2 添加 `inventoryCount` ref，在 `onMounted` 中调用 API 获取 pending+in_progress 任务数量，失败时默认为 0

## 2. 角标绑定

- [x] 2.1 将 `navItems` 从常量数组改为 computed 属性，动态绑定盘点菜单项的 badge 值为 `inventoryCount`（仅当 > 0 时设置）
- [x] 2.2 确认模板中 `v-if="item.badge && !isCollapsed"` 逻辑与新数据源兼容

## 3. 验证

- [x] 3.1 启动前端 dev server，确认侧边栏盘点角标显示正确数字
- [x] 3.2 在后端创建/完成盘点任务，刷新前端确认角标数值对应变化
