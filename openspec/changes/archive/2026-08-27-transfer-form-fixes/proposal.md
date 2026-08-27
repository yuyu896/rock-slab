## Why

2026-08-27 验收测试暴露流转单表单四处缺陷（v2-revision-issues.md 议题 1/2/3/7，已定案于 v2-revision-draft.md 并入设计书修宪记录）：新建页限宽像弹窗、采购金额不自动算、领用行使用人/部门可不填（在用列归属失去依据）、回收单创建页看不到在用数量导致错单提交到审批才炸且报错文案被误读为"无库存"。本案为拆案计划第 1 案，落实修订 1.1 / 2.1 / 2.2 / 1.3。

## What Changes

- **新建/创建页撑满内容区**（修订 1.1）：流转四单共用布局 `TransferCreateLayout` 移除 960px 限宽；盘点任务创建页 `InventoryTaskCreate` 移除 640px 限宽并改为两列栅格；表单栅格在超宽屏可限最大列宽，页面容器不再整体限宽。
- **采购行金额自动计算**（修订 2.1）：明细行金额留空时自动 = 单价 × 数量（前端录入即时联动），手填金额优先；后端对"有单价无金额"的采购行补算（表单与 Excel 导入路径同口径）。
- **领用行使用人/部门必填**（修订 2.2）：不分管理方式（原仅实例管理行强制使用人）；部门字典按所属分公司过滤，未选分公司时部门占位提示"先选分公司"；后端同步强制（表单/编辑/导入共用预检口）。**BREAKING**（导入模板）：领用导入模板新增"使用人"列，领用部门列同步解析为行级部门外键，旧模板文件需重新下载。
- **回收创建页在用预检**（修订 1.3）：回收单创建页选品目后显示（分公司 × 品目）当前在用数量，提交前对在用不足预检拦截（含同品目多行合并计量）；审批端台账不足报错改为业务语言（"回收只能回收『在用』中的资产：当前在用 N…"）。台账 API 增加按品目编号精确过滤参数供预检取数。

## Capabilities

### New Capabilities
- `create-form-fullwidth-layout`: 所有"新建/创建"页面撑满内容区宽度，与列表页同一布局纪律（流转四单 + 盘点任务创建页）。
- `recovery-in-use-precheck`: 回收单创建页的当前在用数量展示与提交预检，审批端在用不足的业务化报错文案。

### Modified Capabilities
- `transfer-create-pages`: 领用明细行使用人/部门必填（原仅实例管理行强制使用人、部门选填）；新增采购行金额留空自动计算规则。
- `transfer-type-templates`: 领用导入模板列变更（新增"使用人"列、部门解析为行级外键）。

## Impact

- **前端**：`views/transfers/components/TransferCreateLayout.vue`（去限宽）、`views/transfers/components/TransferLinesEditor.vue`（金额联动、领用必填、回收在用展示与预检）、`views/inventory/InventoryTaskCreate.vue`（去限宽+两列栅格）、`api/assets.ts`（getAssetStocks 增 asset_code 参数）、`tests/transfers/lineItems.test.ts`（联动与校验用例）。
- **后端**：`apps/transfers/services.py`（validate_line_items_instances 增领用必填校验与采购金额补算）、`apps/transfers/views.py`（assign 导入解析使用人/部门、模板列）、`apps/assets/filters.py`（AssetStockFilterSet 增 asset_code 精确过滤）、`apps/assets/services/ledger.py`（回收在用不足报错文案业务化）。
- **测试**：后端 `tests/test_transfers.py` / `test_import_export.py` / `test_transfer_lines.py` 补用例；前端 vitest + `npm run build` 类型门禁。
- **兼容**：领用 Excel 导入模板列结构变化（旧文件列错位将逐行报错提示）；其余改动对既有 API 消费方无破坏。
