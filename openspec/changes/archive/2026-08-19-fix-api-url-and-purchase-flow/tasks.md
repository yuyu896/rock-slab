## 1. API URL 尾部斜杠修正

- [x] 1.1 修正 `transfers.ts`：列表 URL 保留 `/`，action URL（purchase/assign/return/transfer/repair/scrap/approve）去掉 `/`
- [x] 1.2 审查并修正 `assets.ts`、`users.ts`、`categories.ts`、`branches.ts`、`regions.ts`、`teams.ts`、`inventories.ts` 的 URL

## 2. 采购入库流程修复

- [x] 2.1 `Purchase.vue` 的 `submitOrder` 改用 `purchaseAsset()` 替代 `createAsset()`
- [x] 2.2 `Purchase.vue` 的 `saveDraft` 同样改用 `purchaseAsset()`
- [x] 2.3 传参改用 `to_branch` FK 字段替代 `调入分公司` 字符串

## 3. CSS 变量修复

- [x] 3.1 `variables.css` 添加 `--color-primary` 变量

## 4. 盘点页面 UI 修复

- [x] 4.1 `InventoryTaskList.vue` 筛选栏添加分公司下拉
- [x] 4.2 状态筛选添加"全部状态"默认选项

## 5. 验证

- [ ] 5.1 本地测试采购入库流程正常
- [ ] 5.2 本地测试盘点页面按钮和筛选器正常
- [ ] 5.3 构建并部署到服务器
- [ ] 5.4 生产环境验证
