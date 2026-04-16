## Why

当前盘点模块有两个体验问题：

**问题 1：盘点方式不适配当前使用场景**

当前盘点流程依赖"开始盘点 → 扫码/输入资产编号 → 逐项盘点"的模式，这是为移动端扫描设计的。但在实际 PC 端使用中，用户更习惯线下盘点完成后通过导入 Excel 表格批量上报盘点结果。扫码/输入功能应保留给未来移动端使用，当前阶段以 Excel 导入为主要盘点方式。

**问题 2：任务列表展示效率低**

当前盘点任务以卡片网格（`task-grid`）形式展示，每个任务占一张卡片，包含状态标签、名称、分公司、日期、规则等信息。当任务数量增多时，卡片布局占用大量纵向空间，一屏可展示的任务数有限，不便于快速浏览和对比。改为表格列表形式可以提高信息密度和操作效率。

## What Changes

- 新增盘点 Excel 导入接口：后端 `InventoryTaskViewSet` 增加 `import_result` action，接收 Excel 文件，解析盘点结果（资产编号 + 实盘数量），批量创建/更新 `InventoryItem` 和 `InventoryCheck` 记录
- 前端盘点任务"开始盘点"后增加"导入盘点表"入口：任务状态为 `in_progress` 时，提供 Excel 模板下载和导入上传功能
- 保留扫码/输入功能入口：前端保留现有扫描界面代码，暂不在操作流程中突出展示，待移动端完成后启用
- 任务列表改为表格形式：将 `task-grid` 卡片网格替换为 `<table>` 列表，列包含任务名称、分公司、状态、漏盘规则、重复规则、创建时间、操作按钮

## Capabilities

### New Capabilities

- `inventory-excel-import`: 盘点结果 Excel 批量导入，支持模板下载和文件上传

### Modified Capabilities

- `inventory-task-list`: 任务列表从卡片网格改为表格形式
- `inventory-check-workflow`: 盘点执行流程以 Excel 导入为主要方式，扫码为辅

## Impact

- **后端视图**: `apps/inventories/views.py` 新增 `import_result` 和 `download_template` 两个 action；新增 `InventoryImportSerializer` 校验上传文件
- **前端视图**: `Inventory.vue` 的任务列表区域从卡片网格改为表格；`in_progress` 状态的操作按钮增加"导入盘点表"
- **前端 API**: `inventories.ts` 新增 `importInventoryResult` 和 `downloadInventoryTemplate` 函数
- **依赖**: 后端需 `openpyxl`（项目已有）用于 Excel 解析和模板生成
