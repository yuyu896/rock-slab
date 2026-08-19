## 1. 前端：导出参数透传

- [x] 1.1 `views/AssetList.vue` handleExport 补传 category/status/keyword（branch 保持）；`api/assets.ts` 的 `exportAssets` 参数类型放宽为 `{ branch?, category?, status?, keyword? }`
- [x] 1.2 `views/FixedAssetList.vue` handleExport 补传「资产名称」筛选参数
- [x] 1.3 `composables/useTransferList.ts` handleExport 补传 keyword（type/fromBranch/toBranch/status 保持）

## 2. 后端：端点级回归测试

- [x] 2.1 pytest：`GET /api/assets/export?branch&category&keyword` 断言结果集被筛选过滤
- [x] 2.2 pytest：`GET /api/transfers/export?type=recovery&keyword` 断言结果集被筛选过滤（覆盖 useTransferList 共用后端路径）

## 3. 前端测试（vitest）

- [x] 3.1 AssetList 测试：设置 branch/category/status/keyword 后触发导出，断言 `exportAssets` 收到全部四个参数
- [x] 3.2 FixedAssetList 测试：设置含「资产名称」的全部筛选后触发导出，断言 `exportFixedAssets` 收到全部参数
- [x] 3.3 `useTransferList` 测试：设置 fromBranch/toBranch/status/keyword 后触发导出，断言 `exportTransfers` 参数含 keyword 与 type

## 4. 回归与部署

- [x] 4.1 `npm run build`（类型检查）+ `npm run test` 全量 + 后端 `pytest` 全量通过
- [x] 4.2 本地联调抽查：资产明细筛分类导出、回收列表筛关键词导出，确认 Excel 只含命中数据
- [ ] 4.3 `deploy.sh` 部署生产并验证同路径
