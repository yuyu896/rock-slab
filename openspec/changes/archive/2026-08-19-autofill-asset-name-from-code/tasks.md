## 1. 后端：按编号查询分类接口

- [x] 1.1 `CategoryViewSet` 新增 `lookup` action（`@action(detail=False)`, GET）：按 `asset_code` 精确查询，命中返回 `{ 资产名称, 资产类目, 物品分类, 计量单位 }`，未命中 404，缺参 400
- [x] 1.2 新增后端用例：命中 / 未命中(404) / 缺参(400) / staff 可读

## 2. 前端：查询 helper 与复用组合式

- [x] 2.1 `api/categories.ts` 新增 `lookupCategoryByCode(code)` 调用 `/api/categories/lookup`
- [x] 2.2 新增 `composables/useAssetCodeAutofill.ts`：封装 `lookup(code)` 及 `loading`/`notFoundCode` 状态，供各表单复用

## 3. 接入各新增表单（编号失焦 → 带出 + 未登记提示）

- [x] 3.1 `AssetCreatePage.vue`：编号 `@blur` 带出 名称+资产类目+物品分类（下拉选项取自 allCategories，兼容）
- [x] 3.2 `RecoveryCreate.vue`：编号 `@blur` 带出 名称+类目+分类+单位（均为文本输入）
- [x] 3.3 `AssignCreate.vue` / `TransferCreate.vue` / `transfers/PurchaseCreate.vue`：编号 `@blur` 带出 名称；未登记内联提示
- [x] 3.4 `purchases/PurchaseCreateForm.vue`：每行编号 `@blur` 带出该行名称；未登记 toast + 红框

## 4. 验证

- [x] 4.1 前端类型检查 `vue-tsc --noEmit` 通过
- [x] 4.2 前端测试：`useAssetCodeAutofill` 命中带出 / 未命中提示 / 空编号不请求（3 用例）
- [x] 4.3 后端 `pytest` 全绿（344 passed）
- [ ] 4.4 本地手动验证各表单带出与未登记提示行为

## 5. 收尾

- [x] 5.1 `FixedAssetCreate.vue` 已确认**不纳入**（按编号查 Asset 的既有机制，与本变更不同）
- [x] 5.2 核对各表单类目/分类字段：`AssetCreatePage` 为下拉，选项取自已加载的 `allCategories`，带出值可显示；其余表单为文本输入，无兼容问题
