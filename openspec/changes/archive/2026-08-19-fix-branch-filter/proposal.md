## Why

库存模块「资产列表」的分公司筛选选择某分公司后**看不到对应数据**。根因：前端发送的是分公司**名称**（`b.name`），而后端 `AssetFilterSet.branch` 按 `分公司编号`（**code**）精确过滤——名称 ≠ 编号 → 返回 0 条。

排查「其他列表」发现**流转列表**（领用/采购/调拨/回收）的分公司筛选**同样失效**：前端发送分公司 **id**，后端 `TransferFilterSet.fromBranch/toBranch` 按 `调出分公司/调入分公司`（名称 CharField）过滤，id 永远匹配不上；且表单创建的流转记录 `调出分公司` 字段存的是**空字符串**（仅写了 `from_branch` 外键、名称字段未回填），即便改传名称也匹配不到。「固定资产表」「盘点」的筛选传参与后端一致，正常。

## What Changes

- **资产列表**：分公司下拉值由 `b.name` 改为 `b.code`，与后端 `分公司编号` 过滤对齐。
- **流转列表**（4 个类型）：分公司下拉值由 `b.id` 改为 `b.name`，与后端 `调出分公司/调入分公司`（名称）过滤对齐。
- **后端流转创建**：表单创建流转时，用 `from_branch/to_branch` 外键回填 `调出分公司/调入分公司` 的**名称**（当前表单只传 id、名称字段留空），使名称字段在「表单」与「导入」两种来源下一致存名称，筛选才能命中。
- **固定资产表、盘点**筛选不变（已正确）。

## Capabilities

### New Capabilities
- `branch-filter`: 资产/固定资产/流转/盘点列表按分公司筛选时，前端传值与后端过滤字段一致，能命中对应分公司的数据；并保证流转记录的分公司名称字段被正确写入。

### Modified Capabilities
<!-- 无：现有 specs 中不含分公司筛选 capability。 -->

## Impact

- **前端** `AssetList.vue`（下拉值 name→code）、`composables/useTransferList.ts`（下拉值 id→name）。
- **后端** `apps/transfers/views.py`：创建流转时由 `from_branch/to_branch` 回填 `调出/调入分公司` 名称。
- **测试**：资产按编号筛选命中、流转按名称筛选命中、流转创建回填名称、固定资产筛选回归。
- 无 DB 迁移。
