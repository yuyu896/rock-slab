## 1. 品目新增/编辑改为路由页面

- [x] 1.1 新增 `views/categories/CategoryCreate.vue`，承载新增 + 编辑（编辑模式读路由 `:id` 回填），字段与原 `CategoryForm` 一致
- [x] 1.2 `router/index.ts` 增加 `/categories/create` 与 `/categories/:id/edit` 路由
- [x] 1.3 `Category.vue`："新增分类"按钮改为 `router.push('/categories/create')`；行内"编辑"改为 `router.push('/categories/:id/edit')`；移除 `CategoryForm` 模态与相关状态
- [x] 1.4 create 页面提交成功后 `router.replace('/categories')`

## 2. 盘点创建任务改为路由页面

- [x] 2.1 新增 `views/inventory/InventoryTaskCreate.vue`，字段与原弹窗一致，提交调 `createInventoryTask`
- [x] 2.2 `router/index.ts` 增加 `/inventory/create` 路由
- [x] 2.3 `Inventory.vue`："创建任务"按钮改为 `router.push('/inventory/create')`；移除 `showCreateTaskModal` 弹窗与相关状态/模板/未用 import
- [x] 2.4 create 页面提交成功后 `router.replace('/inventory')`

## 3. 品目写入口按 manage_categories 控制可见性

- [x] 3.1 `Category.vue` 引入 `usePermission()`，取 `canManageCategories`
- [x] 3.2 顶部"新增分类/导入"、行内"编辑/删除"、卡片"编辑"加 `v-if="canManageCategories"`（admin 恒真）
- [x] 3.3 后端 `manage_categories` gating 已就绪兜底（无权限调写接口 403）

## 4. 验证

- [x] 4.1 前端 `npm run build` 通过（类型检查 ✓）
- [ ] 4.2 手动回归：新增/编辑品目、创建盘点任务（提交/取消/返回）；品目写入口权限可见性（待用户验证）
