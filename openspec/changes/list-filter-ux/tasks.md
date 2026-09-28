# 列表筛选持久化与宽度均衡 — 实施任务

## 1. 核心机制：useQueryFilters composable

- [x] 1.1 新建 `frontend/src/composables/useQueryFilters.ts`：init 从 query 反序列化（数组逗号分隔、page 数字、脏值容错）、watch(filters) → `router.replace` 序列化（仅含有值键）、恢复期 skip 标记防误触发
- [x] 1.2 单测：恢复仅一次拉取、页码不重置、query 同步（有值写/空值删）、脏 query 容错、重置清空

## 2. 页面接入（第一批：痛点场景）

- [x] 2.1 `useTransferList.ts` 内嵌接入（采购入库/领用/调拨/回收四列表零改动受益）：status/fromBranch/toBranch/keyword/page 进 query
- [x] 2.2 `FixedAssetList.vue` 接入：branch/status/keyword/pendingSerial/page
- [ ] 2.3 手验路径回归：采购入库列表筛选「待审批」→ 进详情审批 → 返回，筛选与页码保留、数据已刷新

## 3. 页面接入（第二批：其余列表）

- [x] 3.1 `AssetSummary` / `Inventory`（含 `InventoryTaskList`，状态由 Inventory 持有）/ `AuditLog` / `RecoveryLedger` 接入；`FilterPanel` 经查无宿主（死代码）跳过

## 4. 筛选栏宽度

- [x] 4.1 `BranchFilterSelect.vue` 宽度 220px → 300px
- [x] 4.2 各列表页 `.filter-item.search` 加 `max-width: 400px`（含使用处清单核对）
- [ ] 4.3 弹窗内使用处（如 `AdjustRecordsDialog`）目检不溢出

## 5. 验证与收口

- [x] 5.1 全量前端测试 `npm run test` 通过
- [x] 5.2 类型门禁 `npm run build` 通过
- [ ] 5.3 手验清单：往返/刷新/带 query 直达/重置/分享链接；宽屏窄屏筛选栏观感；本地验证后自行部署
