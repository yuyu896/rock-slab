## Why

2026-08-27 验收定案（v2-revision-draft.md 议题 10 → 设计书新增十三节，已入修宪记录）：盘点范围现状只有 分公司×类目 两维且应盘恒取在库列——回收库的资产永远盘不到；"部门盘点"没有落点，行政想核对"谁名下哪几台"只能靠人工比对实例档案。定案为：**盘点任务范围 = 分公司 × 资产类目 × 库别**（差异调整单修对应列），**部门盘点 = 实例盘**（仅实例管理品目，按部门/使用人分组逐台核对，差异不自动改账）。本案为拆案计划（v2-revision-draft.md §八）第 6 案，体量"大"。

## What Changes

- **库别维度（台账盘）**：盘点任务新增 `stock_bin` ∈ {在库, 回收库}（默认在库）。应盘数量取对应台账列；生成盘点项的行集 = 该列 > 0 的台账行；差异调整单的目标列跟随库别（原实现恒修在库列）。
- **部门实例盘**：盘点任务新增可选 `department`（部门字典，须属于任务分公司）；**设置部门即为实例盘**——清单为该部门名下 `状态=在用` 的实例（天然仅实例管理品目；可选类目再过滤），按部门/使用人分组逐台核对（点选打钩 / 扫码内部编号），计数单位是"台"；重复盘点规则对实例盘不适用（一台一勾）。
- **实例盘差异不自动改账**：审批通过不生成台账调整单；盘亏实例在报告标记"待跟进"，报告视图提供**对盘亏项一键发起回收单**（预填跳转回收创建页，走既有审批流，与修订 5.1 回收入口唯一化一致）。
- **创建页盘点方式选择与场景提示**：创建页提供"台账盘点 / 部门实例盘点"切换（库别/部门随之显隐）；重复盘点规则附场景提示文案（累计=多人分区各数各的/逐台扫码逐次累加；以最后一次为准=单人数错重数覆盖）。
- **报告与导出**：报告/Excel 导出对实例盘任务输出应到/实到/缺失汇总 + 缺失明细（到内部编号粒度），按部门/使用人分组；台账盘报告基本信息增库别。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `inventory-item-basis`: 「盘点明细以台账行为基准」增库别维度（应盘取对应列、行集=该列>0）；「盘点差异自动生成调整单」目标列跟随库别且实例盘任务不生成；新增「部门实例盘点」与「实例盘差异处置（不自动改账+待跟进+一键回收）」requirement。
- `inventory-detail-page`: 新增「实例盘清单视图（按使用人分组逐台打钩/扫码）」与「创建页盘点方式选择及规则场景提示」requirement。
- `inventory-report-export`: 报告与 Excel 导出增实例盘汇总与缺失明细（内部编号粒度）；基本信息增库别/部门。

## Impact

- **后端模型/迁移**：`apps/inventories/models.py`（InventoryTask 增 `stock_bin`、`department`；新增 `InventoryInstanceItem` 模型 task×instance）；一个纯 DDL migration（AddField×2 + CreateTable）。
- **后端逻辑**：`views.py`（_generate_items 按库别列、start 生成实例清单、check 期望值按列、新增 check-instance 动作、approve 实例盘跳过改账、progress/report/export 实例口径、_apply_missed_rule 实例项）、`services.py`（adjustments 目标列参数化）、`serializers.py`（新字段 + department∈branch 校验 + 实例项 serializer）。
- **前端**：`views/inventory/InventoryTaskCreate.vue`（方式切换/库别/部门/场景提示）、`views/Inventory.vue`（详情实例盘分组清单与打钩、扫码输入、报告实例视图与盘亏回收入口）、`views/transfers/RecoveryCreate.vue`（query 预填盘亏实例）、`views/MobileScan.vue`（实例盘扫码打钩）、`api/inventories.ts`、`types`、`constants`（库别/盘点方式选项）。
- **测试**：后端 pytest（库别盘全链路、实例盘全链路不改账、部门归属校验、数量品目部门盘空清单）；前端 build + vitest。
- **兼容**：存量任务无 stock_bin 默认在库、无 department 走台账盘——行为与现状完全一致；InventoryInstanceItem 为新表无存量。
