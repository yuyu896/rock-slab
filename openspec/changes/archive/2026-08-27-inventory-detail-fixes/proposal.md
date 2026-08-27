## Why

2026-08-27 验收测试发现盘点任务详情页三处缺陷 + 一处展示缺口（v2-revision-issues.md 议题 9，定案于 v2-revision-draft.md 修订 1.2 并已入设计书修宪记录）：详情页只有三张信息卡看不到盘点物品明细；「导出报告」按钮无事件绑定且后端无导出接口；「继续盘点」按钮是死按钮（有效入口在任务列表行）；按人盘点流水数据已存在（InventoryCheck 表 + checks 接口）但 PC 端无任何展示。本案为拆案计划（v2-revision-draft.md §八）第 2 案，落实修订 1.2。

## What Changes

- **详情页补物品明细表**：盘点任务详情页新增物品明细表（品目编号、名称、应盘、实盘、差异、结果、备注，差异带正负/颜色标记），数据复用报告接口的 items，未开始任务显示空态。
- **详情页补按人盘点流水**：详情页新增盘点流水视图——每次提交一条（盘点人、时间、品目、数量），支持按盘点人筛选查看（"每个员工的盘点表"）。数据取既有 checks 接口；接口增补盘点人筛选参数与展示字段（盘点人姓名、品目编号/名称——现序列化器只回 UUID，PC 端无法展示，手机扫码页最近记录同因字段缺失显示空白，顺带对齐）。
- **报告导出**：后端新增盘点报告 Excel 导出接口（基本信息 + 统计 + 明细 + 完成后所生成调整单的单据编号），前端「导出报告」按钮绑定下载（沿用盘点模板下载的 blob 模式）。
- **删死按钮**：删除详情页「继续盘点」死按钮；继续盘点的有效入口维持任务列表行操作不变。

## Capabilities

### New Capabilities

- `inventory-detail-page`: 盘点任务详情页内容完整性——物品明细表（含差异标记）、按人盘点流水（筛选查看）、无效死控件清除。
- `inventory-report-export`: 盘点报告 Excel 导出——基本信息、统计、明细、所生成调整单号四段内容与前端入口。

### Modified Capabilities

（无——报告 JSON 接口与 checks 接口的既有行为不变，新增字段/参数均为增量。）

## Impact

- **后端**：`apps/inventories/views.py`（新增 `export-report` action，openpyxl 生成，模式同 `download_template`；`checks` action 增 `checked_by` 过滤参数）、`apps/inventories/serializers.py`（`InventoryCheckSerializer` 增 `checked_by_name`/`asset_code`/`asset_name` 展示字段）。只读路径，无模型/迁移变更；权限沿用（读操作不要求操作码，DataScope 过滤）。
- **前端**：`views/Inventory.vue`（详情视图增明细表与流水卡、绑导出、删死按钮）、`api/inventories.ts`（增 `exportInventoryReport`）、`views/MobileScan.vue`（最近记录字段对齐新展示字段，修复空白显示）。
- **测试**：后端 `tests/` 补导出接口（四段内容、调整单号）与 checks 过滤/字段用例；前端 `npm run build` 类型门禁。
- **兼容**：全部为增量接口/字段，对既有消费方无破坏。
