## Why

各列表页的「导出」按钮导出的数据不遵循页面当前筛选：资产明细只传了分公司（分类/状态/关键词被忽略），固定资产漏传资产名称筛选，四个流转列表漏传关键词。用户期望"所见即所得"——筛了分公司 + 分类，导出的 Excel 就只含这些数据。后端各 export 端点均已走 `filter_queryset` 天然支持全部筛选参数，缺口集中在前端漏传。

## What Changes

- **资产明细**（`AssetList.vue`）：导出透传当前全部筛选——分公司、资产类目、状态、关键词
- **固定资产**（`FixedAssetList.vue`）：导出补传「资产名称」筛选（现有分公司/状态/关键词保持）
- **流转四列表**（采购/领用/调拨/回收，共用 `composables/useTransferList.ts`）：导出补传关键词（现有分公司/状态/类型保持）
- **资产汇总、品目**：导出已完整遵循筛选，本次以规格固化现状防回归，不改代码
- 前端 vitest 断言各导出调用携带全部筛选参数；后端补少量 export 端点带筛选的回归测试
- **不新增导出功能**：盘点/用户/组织/审计日志等无导出的页面不在范围内；旧页 `Purchase.vue`（`/assets/purchase`）无菜单入口（遗留路由），不投入修改

## Capabilities

### New Capabilities
- `export-filter-alignment`: 已有导出功能的库存与流转列表，导出数据集与页面当前筛选结果一致

### Modified Capabilities

（无）

## Impact

- **前端**：`views/AssetList.vue`、`views/FixedAssetList.vue`、`composables/useTransferList.ts` 三处 `handleExport` 参数透传；`api/assets.ts` 的 `exportAssets` 参数类型放宽
- **测试**：前端 vitest 新增导出参数断言；后端 pytest 补 export 端点筛选回归
- **后端**：预期零改动（已验证 `filter_queryset` 支持），如个别 filter 缺口则最小补齐
- **部署**：纯代码变更无迁移，走 `deploy.sh` 常规流程
