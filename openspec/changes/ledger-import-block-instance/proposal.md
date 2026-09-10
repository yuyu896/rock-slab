# 台账批量导入禁止实例管理品目

## Why

台账增量导入（差异预览/confirm 生成调整单）当前不校验品目管理方式：员工可把**实例管理**品目导入台账，经调整单直改其「在库」列。实例品目的在库列是实例镜像（=在库实例计数，铁律下只能经采购单/流转单变动），被导入直改后与实例计数永久分裂——生产 23 处对账差异中即有此类成因。数量管理/消耗品品目不受影响（台账导入本就是其合规路径）。

## What Changes

- `_parse_import_rows` 行级校验：品目命中字典后，若 `management_type == 'instance'` 计入行级错误（提示「实例管理品目不可台账导入，数量经采购入库单/流转单变动」）跳过——预览（diffs）与 confirm（applied）两阶段天然拦截（错误行不产生差异）
- 前端台账导入弹窗（SummaryImportDialog）补提示文案：实例管理品目不支持台账导入
- 非目标：数量管理/消耗品导入行为不变；存量 23 处对账差异的修复另行提案（走调整单补平）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `asset-batch-import`: 台账增量导入新增行级守卫——实例管理品目拒入

## Impact

- **后端**: `apps/assets/views.py` `_parse_import_rows`（行级校验 + 测试）
- **前端**: `SummaryImportDialog.vue`（提示文案）
- 测试：实例品目行被拦（预览/confirm 两阶段）、数量/消耗品行不受影响
