## 盘点 Excel 导入 + 列表视图 — 任务清单

### 后端：Excel 导入

- [ ] T1: `apps/inventories/views.py` — 新增 `download_template` action，根据任务范围生成含应盘资产的 Excel 模板
- [ ] T2: `apps/inventories/views.py` — 新增 `import_result` action，解析 Excel 批量更新 InventoryItem + 创建 InventoryCheck
- [ ] T3: `apps/inventories/views.py` — 修改 `start` action，开始盘点时预生成 InventoryItem（筛选分公司+类目范围的资产）

### 前端：列表视图

- [ ] T4: `Inventory.vue` — 将 `task-grid` 卡片网格替换为 `<table>` 表格，列：任务名称、盘点范围、状态、漏盘规则、重复规则、创建时间、操作
- [ ] T5: `Inventory.vue` — 操作按钮从卡片底部移到表格行尾，保持按状态显示不同按钮组的逻辑
- [ ] T6: `Inventory.vue` — 移除卡片相关 CSS，新增表格样式

### 前端：Excel 导入 UI

- [ ] T7: `api/inventories.ts` — 新增 `downloadInventoryTemplate` 和 `importInventoryResult` API 函数
- [ ] T8: `Inventory.vue` — `in_progress` 状态操作按钮增加"下载模板"和"导入盘点表"按钮
- [ ] T9: `Inventory.vue` — 导入完成后显示成功/失败提示，刷新任务列表

### 验证

- [ ] T10: 创建盘点任务 → 开始盘点 → 下载模板确认包含应盘资产 → 填写实盘数量 → 导入 → 校验 InventoryItem 结果正确
- [ ] T11: 确认任务列表以表格形式展示，操作按钮按状态正确显示
