## 1. 盘点期间库存锁定

- [ ] 1.1 `backend/apps/inventories/views.py` — 在 `start` action 中增加并发盘点校验：查询同分公司是否已有 status in ['in_progress', 'pending_review'] 的任务，若有则返回 400 错误
- [ ] 1.2 `backend/apps/inventories/models.py` — 为 InventoryTask 模型的 Meta 类添加数据库索引 `indexes = [Index(fields=['branch', 'status'])]`，加速锁定查询
- [ ] 1.3 `backend/apps/inventories/views.py` — 在 `approve` action 中，库存调整完成后检查该分公司是否还有其他活跃盘点任务，若无则表示自然解锁
- [ ] 1.4 `backend/apps/inventories/views.py` — 在 `cancel` action 中，状态变更后同样检查是否需要解锁（逻辑同上，动态查询已自动处理）

## 2. 流转操作拦截

- [ ] 2.1 `backend/apps/transfers/views.py` — 新增辅助方法 `_check_inventory_lock(asset_branch_code)`，查询该分公司是否存在 status in ['in_progress', 'pending_review'] 的 InventoryTask，若存在则抛出 ValidationError 并附带 `INVENTORY_LOCKED` 错误码和任务信息
- [ ] 2.2 `backend/apps/transfers/views.py` — 在 `perform_create` 或各 action（purchase/assign/return/transfer/repair/scrap）的创建逻辑中调用 `_check_inventory_lock`，在资产数量被修改前进行拦截
- [ ] 2.3 `frontend/src/utils/request.ts` 或各流转页面 — 前端处理 `INVENTORY_LOCKED` 错误码，显示"该分公司正在进行盘点，暂无法进行此操作"的提示信息

## 3. 前端并发盘点提示

- [ ] 3.1 `frontend/src/views/Inventory.vue` — 在创建盘点任务时，若用户选择分公司，可提示该分公司是否已有进行中的盘点任务（可选优化，非必须）

## 4. 驳回后选择性重盘

- [ ] 4.1 `backend/apps/inventories/serializers.py` — 新增 `RecountSerializer`，包含 `reset_scope` 字段（choices: ['all', 'abnormal_only']，默认 'all'）
- [ ] 4.2 `backend/apps/inventories/views.py` — 修改 `recount` action，从请求体读取 `reset_scope`。若为 `all`（默认），保持当前行为重置所有盘点项；若为 `abnormal_only`，仅重置 result in ['surplus', 'missing', 'unchecked'] 的盘点项，result='matched' 的项保持不变
- [ ] 4.3 `frontend/src/views/Inventory.vue` — 修改重新盘点按钮交互：点击后弹出选择框，提供"重盘全部"和"仅重盘异常项"两个选项，调用 recount API 时传入 `reset_scope` 参数
- [ ] 4.4 `frontend/src/api/inventories.ts` — 修改 `recountInventory` 函数签名，接受可选的 `resetScope` 参数

## 5. 盘点报告增强

- [ ] 5.1 `backend/apps/inventories/views.py` — 修改 `report` action 返回数据，在 progress 对象中增加 `matchRate`（正常率百分比）、`surplusRate`（盘盈率）、`missingRate`（缺失率）字段
- [ ] 5.2 `backend/apps/inventories/serializers.py` — 修改 `InventoryProgressSerializer`，增加 `matchRate`、`surplusRate`、`missingRate` 浮点数字段
- [ ] 5.3 `frontend/src/types/index.ts` — 在 `InventoryProgress` 接口中增加 `matchRate?`、`surplusRate?`、`missingRate?` 字段
- [ ] 5.4 `frontend/src/views/Inventory.vue` — 修改报告弹窗：在统计区域增加差异率显示；在明细表格中增加"变动数量"列（actualQty - expectedQty）
