## Why

资产流转模块两处不便：

1. **采购入库详情是弹窗、且驳回后不能改**：当前「详情」是模态弹窗，信息有限；被驳回的采购入库单没有修改入口，无法修正后重新提交。用户期望详情打开**独立页面**看完整内容，并能在**驳回后修改重新提交**。
2. **新增领用出库只支持单物品**：「新增采购入库」已支持多物品（多行），而「新增领用出库」只能一次填一个物品——应同样支持一次添加多个物品。

## What Changes

1. **采购入库详情独立页**：
   - 新增路由 `transfers/purchase/:id` + `PurchaseDetail.vue`；`PurchaseList` 的「详情」按钮跳转该页（取代弹窗），展示完整入库单内容。
   - **驳回可修改重提**：详情页对「已驳回」记录提供编辑（修改字段）+「重新提交」（已驳回→待审批）。
   - 后端新增 `resubmit` 动作（已驳回→待审批）；`update` 仅允许对「已驳回」编辑字段（其他状态不可改）。
2. **领用出库多物品**：
   - `AssignCreate.vue` 改为多行物品表单（参照 `PurchaseCreateForm`）：共享 调拨日期/分公司/备注，每行 资产编号/资产名称/数量/使用人；提交逐行创建领用流转。

## Capabilities

### New Capabilities
- `transfer-detail-and-multi-assign`: 采购入库详情改独立页且驳回可修改重提；领用出库支持多物品。

### Modified Capabilities
<!-- 无：现有 specs 中不含这两项 capability。 -->

## Impact

- **前端** 新增 `PurchaseDetail.vue` + 路由 `transfers/purchase/:id`；`PurchaseList.vue` 详情改跳转；`AssignCreate.vue` 多行化（参照 `PurchaseCreateForm`）。
- **后端** `apps/transfers/views.py`：新增 `resubmit` 动作；`update`/`partial_update` 限制为仅「已驳回」可编辑。
- **测试**：`resubmit`（已驳回→待审批、非已驳回拒绝）；多物品领用创建多条流转。
- 无 DB 迁移。
