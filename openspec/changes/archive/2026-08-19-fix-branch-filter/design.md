## Context

四个列表的分公司过滤后端期望不同标识：

- `AssetFilterSet` / `FixedAssetFilterSet`：`branch = CharFilter(field_name='分公司编号')` → **编号(code)**。
- `TransferFilterSet`：`fromBranch/toBranch = CharFilter(field_name='调出/调入分公司')` → **名称(name)**。
- `InventoryTaskFilterSet`：`branchId = CharFilter(field_name='branch_id')` → **id**。

前端各列表下拉 `value` 不一致：`AssetList`=`b.name`(应为 code)、`FixedAssetList`=`b.code`(对)、`Inventory`=`b.id`(对)、`useTransferList`=`b.id`(应为 name)。此外流转**表单创建**只传 `from_branch`(id)，`调出分公司` CharField 留空（仅导入来源写了名称）。

## Goals / Non-Goals

**Goals:**
- 资产列表、流转列表的分公司筛选都能命中对应数据。
- 流转记录的 `调出/调入分公司` 名称字段在表单与导入来源下一致。
- 不破坏已正确的固定资产表、盘点筛选。

**Non-Goals:**
- 不把所有筛选统一为单一标识（各模型存储字段不同，按各自存储字段过滤最稳）。
- 不回溯修复历史「空 调出分公司」数据（仅修创建逻辑，保证新数据正确）。

## Decisions

### 决策 1：资产列表前端发 code（对齐 分公司编号）
- **做法**：`AssetList.vue` 分公司下拉 `value` 由 `b.name` 改为 `b.code`。
- **理由**：后端按 `分公司编号` 过滤；固定资产列表已用 code 且正确，保持一致。
- **备选**：改后端按 `分公司`(name) 过滤——会与固定资产不一致，**否**。

### 决策 2：流转列表前端发 name + 后端创建回填名称
- **做法**：`useTransferList.ts` 下拉 `value` 由 `b.id` 改为 `b.name`；后端流转创建时 `调出/调入分公司 = from_branch/to_branch.name`（外键存在时）。
- **理由**：后端按 `调出/调入分公司`（名称）过滤；导入来源已写名称，表单来源补齐名称后两种来源一致，筛选命中。
- **备选**：改后端按 `from_branch` 外键过滤——但导入来源未设外键会漏，**否**。

### 决策 3：固定资产表、盘点不动
- 它们的传参与后端已一致，保持现状，仅在测试中回归覆盖。

## Risks / Trade-offs

- **[历史空名称数据]** 表单创建的旧流转记录 `调出分公司` 为空，按名称筛选仍漏 → **缓解**：本变更修创建逻辑保证新数据有名称；历史数据可选脚本回填（Open Questions）。
- **[分公司同名]** 名称理论上可能重复 → **缓解**：分公司名称受控、实践中唯一；如需可后续改按编号统一。
- **[导入名称与下拉名称不一致]** 导入 Excel 的分公司名与组织架构登记名不符则筛选漏 → **缓解**：属数据质量，导入校验已在另一变更（分公司存在性）覆盖。

## Migration Plan

1. 前端：`AssetList.vue`、`useTransferList.ts` 下拉值调整。
2. 后端：流转创建回填名称。
3. 纯前后端逻辑，**无 DB 迁移**；部署即生效。

## Open Questions

1. 是否回填历史「空 调出分公司」的流转数据？默认**不回填**（新数据正确即可）。
