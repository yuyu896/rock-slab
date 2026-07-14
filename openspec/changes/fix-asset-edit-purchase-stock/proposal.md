## Why

三处资产/采购流程问题：

1. **资产列表编辑报错**：编辑物品（如改「当前状态」）提交即报错。根因：`updateAsset` 用 **PUT 全量更新**，而编辑抽屉只提交部分字段（资产编号为只读未提交），`资产编号` 是必填 → 全量校验失败报错。
2. **采购入库「保存草稿」未实现**：`saveDraft` 与「提交审批」调用同一 `submitPurchaseItems`（创建「待审批」单），并无草稿状态（审批状态仅有 待审批/已通过/已驳回/已入库）——「保存草稿」实际等于提交。
3. **采购入库审批通过后库存不变**：`approve` 的资产联动（`_sync_asset`）只覆盖 领用/退还/调拨，**采购无联动**；库存仅在单独的「入库确认」(warehouse) 步骤更新。用户期望审批通过即入库。

## What Changes

1. **资产编辑**：`updateAsset` 由 PUT 改 **PATCH**（部分更新），编辑抽屉部分字段提交不再因缺资产编号报错。
2. **采购草稿**：
   - `Transfer` 审批状态新增「草稿」。
   - 采购创建支持 `draft` 标志：草稿→审批状态=「草稿」（不进入审批流）；提交→「待审批」。
   - 前端「保存草稿」以草稿创建；采购列表显示草稿，并提供「提交」将草稿转为「待审批」。
3. **采购审批入库联动**：
   - 抽出库存更新逻辑为公共方法 `_apply_warehouse_stock(transfer)`（存在则累加数量、不存在则创建资产）。
   - `approve` 对采购类型在通过时调用该方法并置「已入库」——审批通过即入库、库存增加。

## Capabilities

### New Capabilities
- `asset-purchase-fixes`: 资产编辑改部分更新、采购草稿（保存/提交）、采购审批通过联动入库三处修复。

### Modified Capabilities
<!-- 无：现有 specs 中不含这三项的 capability。 -->

## Impact

- **前端** `api/assets.ts`（PUT→PATCH）、`Purchase.vue`（saveDraft 以草稿创建）、`PurchaseList.vue`（草稿显示 + 提交草稿）、`api/transfers.ts`（draft 参数 / submitDraft）。
- **后端** `apps/transfers/models.py`（审批状态加「草稿」，含一个无数据变更的 choices 迁移）、`apps/transfers/views.py`（`_create_action` 支持 draft、新增 submit-draft 动作、`_apply_warehouse_stock` 公共方法、`approve` 采购联动入库）。
- **测试**：资产 PATCH 编辑成功；采购草稿创建/提交；采购审批后库存增加/资产创建。
