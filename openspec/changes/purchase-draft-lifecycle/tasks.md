## 1. 前端

- [ ] 1.1 `PurchaseCreate.vue`：操作区增「存为草稿」次级按钮（同一校验，`draft: true` 调既有 createTransfer），成功提示并跳详情或留页（沿既有提交后跳转模式）
- [ ] 1.2 `PurchaseDetail.vue`：`withdrawDoc` 成功后调 `startEdit('draft')`（删去停留在草稿态的中间步）
- [ ] 1.3 `useTransferList.ts` stats 增 `draft` 计数；`PurchaseList.vue` 统计卡区加「草稿」卡
- [ ] 1.4 前端用例：双按钮各自调用参数正确（draft 标志）、撤回成功后 editing 为 true

## 2. 验证收尾

- [ ] 2.1 vitest 全量 + `npm run build` 通过；后端 pytest 回归（草稿建单既有用例不破）
- [ ] 2.2 拆 feat + openspec 两 commit，push
- [ ] 2.3 手验：存草稿→列表见草稿卡→详情撤回直达编辑→保存并提交全链路
