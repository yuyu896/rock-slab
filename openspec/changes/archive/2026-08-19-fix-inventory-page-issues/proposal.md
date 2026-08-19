# 修复盘点页面 UI 问题

## 问题

1. **"创建盘点任务"按钮不可见**：按钮代码存在于 `InventoryTaskList.vue`，但 `.btn-primary` 样式中 `color: #fff` 可能被全局样式覆盖，导致白色文字在浅色背景上不可见。
2. **筛选栏缺少分公司下拉**：`InventoryTaskList.vue` 的筛选区只有关键字搜索和状态筛选，`branchOptions` prop 已传入但未在模板中渲染分公司选择器。

## 影响范围

- `frontend/src/views/inventory/InventoryTaskList.vue` — 筛选栏和按钮
- `frontend/src/views/Inventory.vue` — 父组件状态管理

## 修复方案

1. 检查并修复 `.btn-primary` 按钮样式，确保"创建盘点任务"按钮始终可见
2. 在筛选区添加分公司下拉选择器，使用已有的 `branchOptions` prop
