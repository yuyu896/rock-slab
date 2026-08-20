## 1. 布局骨架

- [x] 1.1 MainLayout：`.main` 改 `height: 100vh`，`.content` 加 `display: flex; flex-direction: column; min-height: 0;`（保留 overflow-y: auto 与内边距）
- [x] 1.2 styles/global.css：新增 `.content > * { flex-shrink: 0; }` 与 `.page-fill { flex: 1 1 0; min-height: 0; display: flex; flex-direction: column; }` 工具类
- [x] 1.3 BasePagination：默认 `pageSize` 20→50（pageSizes 选项保持 [10,20,50,100]），组件根加 `flex-shrink: 0` 供钉底

## 2. 资产三页（去魔法数字）

- [x] 2.1 AssetList.vue：根节点加 `.page-fill`；页头/筛选/批量操作栏 `flex-shrink: 0`；`.table-container` 删 `max-height: calc(100vh - 340px)`，改 `flex: 1; min-height: 200px;`；初始 `pageSize` 20→50
- [x] 2.2 FixedAssetList.vue：同 2.1（sticky 表头已有，保留）
- [x] 2.3 assets/AssetSummary.vue：同 2.1；`pageSize` 20→50

## 3. 四类流转单列表

- [x] 3.1 useTransferList.ts：`pagination` 初始 `pageSize` 20→50
- [x] 3.2 PurchaseList.vue：根节点加 `.page-fill`；统计卡/筛选 `flex-shrink: 0`；`.table-container` `overflow: hidden`→`auto`、加 `flex: 1; min-height: 200px;`；表头加 sticky
- [x] 3.3 AssignList.vue / TransferList.vue：同 3.2
- [x] 3.4 RecoveryList.vue：同 3.2（其容器原为 overflow-x: auto，补 overflow-y: auto）

## 4. 其余列表页

- [x] 4.1 Category.vue：根节点加 `.page-fill`；表格视图容器与卡片视图容器均 `flex: 1; min-height: 0; overflow-y: auto`，表头 sticky；自定义分页默认每页 50（选项 20/50/100 保留）；初始 `pageSize` 20→50
- [x] 4.2 AuditLog.vue：根节点加 `.page-fill`（去掉与内容区重复的 padding）；`.log-table-container` 改 `flex: 1; min-height: 400px→200px; overflow-y: auto`，表头 sticky；`pageSize` ref 20→50
- [x] 4.3 Inventory.vue + inventory/InventoryTaskList.vue：`.inventory-page` 加 `.page-fill` + `overflow-y: auto`（多视图）；InventoryTaskList 根节点 `flex: 1; min-height: 0`，`.task-table-wrapper` `flex: 1; overflow-y: auto`，表头 sticky；初始 `pageSize` 20→50
- [x] 4.4 Purchase.vue：`.purchase-page` 加 `.page-fill` + `overflow-y: auto`（多视图）；列表视图容器与 `.table-container` 同范式改造，表头 sticky

## 5. 验证与回归

- [x] 5.1 更新受影响测试（AssetSummary.test.ts 的 pageSize 断言 20→50），为 BasePagination 默认每页 50 补一条组件断言
- [x] 5.2 `npm run test` 全绿、`npm run build`（含类型检查）通过
- [x] 5.3 逐页走查 PC 路由：列表页表格撑满/分页贴底/表头常驻；工作台、新建、详情、组织、报表页滚动行为与改造前一致
