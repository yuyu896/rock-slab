## Why

采购入库已有独立详情页（PurchaseDetail.vue）+ 驳回编辑重提能力，但领用出库和调拨仍用弹窗看详情、不支持编辑重提。需要统一为独立详情页 + 编辑重提，与采购入库一致。

## What Changes

1. **领用出库详情页**：新增 `AssignDetail.vue` + 路由 `transfers/assign/:id`；AssignList 详情按钮跳转独立页；对「已驳回」支持编辑全部字段 + 重新提交。
2. **调拨详情页**：新增 `TransferDetail.vue` + 路由 `transfers/transfer/:id`；TransferList 详情按钮跳转独立页；对「已驳回」支持编辑 + 重新提交。
3. **后端**：`resubmit` 动作和 `perform_update`（限已驳回）已是通用的（不区分 action_type），无需改动。

## Capabilities

### New Capabilities
- `assign-transfer-detail-pages`: 领用出库和调拨的独立详情页 + 驳回编辑重提。

### Modified Capabilities
<!-- 扩展 transfer-detail-and-multi-assign（采购详情已有，扩展到领用/调拨）。 -->
