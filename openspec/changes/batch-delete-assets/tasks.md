## 1. 后端 batch_delete

- [x] 1.1 `AssetViewSet` 新增 `batch_delete` action（`@action(detail=False, methods=['post'])`）：接收 `{ ids: [...] }`，`get_queryset().filter(id__in=ids).delete()`（事务内），返回 `{ deleted: <count> }`；`required_operations` 加 `'batch_delete': 'manage_assets'`
- [x] 1.2 `FixedAssetViewSet` 同上（共享 `_batch_delete` 助手）
- [x] 1.3 后端测试：batch_delete 命中计数、越权 id 被数据范围排除、无 `manage_assets` 返回 403、空 ids 400、固定资产批量删除（共 5 用例）

## 2. 前端 api

- [x] 2.1 `api/assets.ts` 新增 `batchDeleteAssets(ids)` / `batchDeleteFixedAssets(ids)`（POST 对应 batch-delete 端点）

## 3. 前端：资产列表

- [x] 3.1 `AssetList.vue` 既有批量操作栏新增「批量删除」按钮（`canManageAssets` 网关）；新增 `handleBatchDelete`：未选提示 → `ElMessageBox` 确认（含数量）→ 调 `batchDeleteAssets` → 成功提示 → 刷新 + 清空 `selectedAssets`；加 `.batch-btn.danger` 样式

## 4. 前端：固定资产表

- [x] 4.1 `FixedAssetList.vue` 新增行复选框 + 表头全选 + `selectedIds`/`isAllSelected`/`toggleAll`/`toggleSelect`
- [x] 4.2 新增批量操作栏（有选择且 `canManageAssets` 时显示）含「批量删除」按钮 + `handleBatchDelete`；加 `.fa-batch-*` / `.col-check` 样式

## 5. 验证

- [x] 5.1 后端 `pytest` 全绿（353 passed）
- [x] 5.2 前端 `vue-tsc --noEmit` 通过（exit 0）
- [ ] 5.3 本地手动验证：两表勾选多条 → 批量删除 → 刷新 + 清空选择；无权限者看不到入口
