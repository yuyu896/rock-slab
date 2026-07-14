## 1. 资产编辑（PATCH）

- [x] 1.1 `api/assets.ts` `updateAsset`：`request.put` → `request.patch`
- [x] 1.2 测试：PATCH 仅改状态编辑成功（不因缺资产编号报错）

## 2. 采购草稿

- [x] 2.1 `apps/transfers/models.py` `APPROVAL_CHOICES` 加 `('草稿','草稿')`（已生成迁移 0008）
- [x] 2.2 后端 `_create_action` 支持 payload 的 `draft` 标志：草稿→审批状态「草稿」，否则「待审批」
- [x] 2.3 后端新增 `submit` 动作（detail）：草稿→待审批（非草稿拒绝）
- [x] 2.4 前端 `api/transfers.ts`：`purchaseAsset` 加 `draft?`；新增 `submitTransfer`
- [x] 2.5 前端 `Purchase.vue` `saveDraft` 传 `draft=true`；`submitPurchaseItems(order, draft)`
- [x] 2.6 前端 `PurchaseList.vue`：草稿记录显示「提交」按钮（行 + 详情弹窗）调 `submitTransfer`
- [x] 2.7 类型/常量：`ApprovalStatus` 加「草稿」；`APPROVAL_STATUS_OPTIONS`/`COLORS` 补草稿项
- [x] 2.8 测试：草稿创建（状态=草稿）；提交草稿（→待审批）

## 3. 采购审批入库联动

- [x] 3.1 后端抽出 `_apply_warehouse_stock(transfer)` 公共方法（调入/调出回退解析入库分公司；存在累加、不存在创建）
- [x] 3.2 `approve` 对采购类型通过时调用 `_apply_warehouse_stock` 并置「已入库」
- [x] 3.3 移除冗余「入库」：后端 `warehouse` 动作、前端 `warehouseTransfer` API、`PurchaseList` 两处「入库」按钮与 `handleWarehouse`（保留「已入库」状态/统计）
- [x] 3.4 测试：采购审批通过后库存增加（资产存在）/ 创建（资产不存在）；既有 approve 用例改判「已入库」

## 4. 验证

- [x] 4.1 后端 `pytest` 全绿（365 passed）
- [x] 4.2 前端 `vue-tsc --noEmit` 通过（exit 0）
- [ ] 4.3 本地手动验证：资产编辑改状态成功；采购保存草稿/提交草稿；采购审批通过后库存增加
