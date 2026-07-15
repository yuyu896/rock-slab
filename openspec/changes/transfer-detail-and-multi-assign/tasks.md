## 1. 采购入库详情独立页

- [x] 1.1 新增路由 `transfers/purchase/:id` + `PurchaseDetail.vue`（展示完整入库单内容）
- [x] 1.2 `PurchaseList.vue`「详情」按钮改 `router.push` 到详情页（移除详情弹窗及未用解构 `viewDetail/showDetailModal/detailItem/typeColor`）

## 2. 驳回可修改并重新提交

- [x] 2.1 后端 `apps/transfers/views.py` 新增 `resubmit` 动作：仅「已驳回」→「待审批」，否则 400
- [x] 2.2 后端 `perform_update` 限制：仅「已驳回」可改字段，其他状态 400
- [x] 2.3 详情页 `PurchaseDetail.vue`：对「已驳回」显示编辑表单（**所有字段均可改**）+「保存并重新提交」
- [x] 2.4 前端 `api/transfers.ts` 新增 `resubmitTransfer`、`updateTransfer`
- [x] 2.5 测试：update 已驳回成功、非已驳回 400；resubmit 已驳回→待审批、非已驳回 400（4 用例）

## 3. 领用出库多物品

- [x] 3.1 `AssignCreate.vue` 改多行物品表单（共享 日期/分公司/备注，每行 资产编号/资产名称/数量/使用人；增删行）
- [x] 3.2 提交逐行 `assignAsset`
- [x] 3.3 `Transfer` 类型补 `供应商/单价/总金额/需求部门`

## 4. 验证

- [x] 4.1 后端 `pytest` 全绿（369 passed）
- [x] 4.2 前端 `vue-tsc --noEmit` 通过（exit 0）
- [ ] 4.3 本地手动验证：采购详情独立页、驳回编辑重提、领用多物品提交
