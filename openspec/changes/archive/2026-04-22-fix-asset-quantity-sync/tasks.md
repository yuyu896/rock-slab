## 1. 后端 — 删除维修/报废功能

- [x] 1.1 `transfers/models.py`：从 ACTION_TYPE_CHOICES 中移除 repair 和 scrap 选项
- [x] 1.2 `transfers/views.py`：删除 repair 和 scrap 的 action 端点
- [x] 1.3 `transfers/serializers.py`：从 TransferActionSerializer 的 action_type 校验中移除 repair/scrap

## 2. 后端 — 资产流转同步

- [x] 2.1 `transfers/views.py`：在 `approve()` 方法中，审批通过后根据 `action_type` 调用对应的 Asset 更新逻辑
- [x] 2.2 实现 `_sync_assign(transfer)` — Asset 状态改为"使用中"
- [x] 2.3 实现 `_sync_return(transfer)` — Asset 状态改为"在库"
- [x] 2.4 实现 `_sync_transfer(transfer)` — Asset 分公司/区域更新为目标分公司
- [x] 2.5 每个 `_sync_*` 方法使用 `transaction.atomic()` + `select_for_update()` 保证并发安全

## 3. 后端 — Category 计数修复

- [x] 3.1 `categories/models.py`：新增 `asset_total_quantity` 和 `in_stock_quantity` 字段
- [x] 3.2 `categories/signals.py`：计数逻辑从 `.count()` 改为 `Sum('数量')` 聚合
- [x] 3.3 `categories/serializers.py`：序列化器中暴露新字段

## 4. 前端适配

- [x] 4.1 `constants/index.ts`：从操作类型常量中移除 repair/scrap
- [x] 4.2 `types/index.ts`：Category 类型定义新增 `assetTotalQuantity` 和 `inStockQuantity` 字段
- [x] 4.3 流转相关页面：移除维修/报废选项的 UI 展示
- [x] 4.4 分类管理页面：展示资产总数量而非仅行数

## 5. 测试

- [x] 5.1 后端单元测试：领用审批后 Asset 状态变为"使用中"
- [x] 5.2 后端单元测试：调拨审批后 Asset 分公司变更
- [x] 5.3 后端单元测试：repair/scrap 端点返回 405
- [x] 5.4 后端单元测试：Category 计数使用 Sum 聚合

## 6. 验证

- [ ] 6.1 手动验证：完整流程 — 采购入库→领用→调拨→归还，每步检查 Asset 状态
