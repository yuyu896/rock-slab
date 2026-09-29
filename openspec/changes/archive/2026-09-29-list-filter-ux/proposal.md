# 列表筛选状态持久化与筛选栏宽度均衡（list-filter-ux）

## Why

两个 PC 列表页筛选的体验问题（2026-09-28 用户反馈）：

1. **详情页往返筛选丢失**：列表页筛选条件存在组件局部 `ref`，路由 `<router-view />` 无 keep-alive——进详情页（如审批采购入库时查单据详情）再返回，列表组件销毁重建、筛选全部归零，高频往返流程每次都要重选。属全部列表页通病。
2. **筛选栏宽度失衡**：搜索框 `flex: 1` 独占剩余宽度（宽屏下数百至近千 px），分公司下拉固定 220px（长分公司名与多选标签拥挤）。

## What Changes

- **筛选+页码写路由 query（全部 PC 列表页）**：筛选变更即同步到 URL query（`router.replace`，不污染历史）；进入/返回页面时从 query 恢复筛选与页码再重新拉取数据——返回保留筛选且数据新鲜（审批/操作后回来状态已更新）；带 query 的链接可直接打开对应筛选视图（分享/收藏友好）。**不做**页面缓存（keep-alive），避免旧数据问题。
- **接入页面**：流转四列表（采购入库/领用/调拨/回收，经 `useTransferList`）、固定资产实例、资产汇总、盘点（任务列表）、审计日志、回收台账等持有本地筛选的 PC 列表页。
- **筛选栏宽度统一**：搜索框 `max-width: 400px`；`BranchFilterSelect` 220px → 300px；所有使用处（含弹窗内）随组件统一。
- 实现关键坑（详见 design）：从 query 恢复初始化时须跳过「watch 触发重置页码/重复拉取」；手动重置按钮同步清空 query。

## Capabilities

### New Capabilities

- `list-filter-ux`：PC 列表页筛选状态的路由持久化（恢复、重拉、query 双向同步）与筛选栏宽度规范。

### Modified Capabilities

（无——`branch-filter` 等既有 spec 只管筛选命中语义，本变更不改过滤逻辑。）

## Impact

- `frontend/src/composables/useQueryFilters.ts`（拟新建：query↔筛选双向同步 composable）、`useTransferList.ts`（接入）。
- 列表页：`PurchaseList` / `AssignList` / `TransferList` / `RecoveryList` / `FixedAssetList` / `AssetSummary` / `Inventory`（含 `InventoryTaskList`）/ `AuditLog` / `RecoveryLedger` 及 `FilterPanel` 使用处。
- `frontend/src/components/BranchFilterSelect.vue`（宽度 300px）+ 各列表页搜索框限宽 CSS。
- 不涉及后端与数据模型（query 参数沿用现有 API 过滤参数）。提案审查两问：无信息双存（筛选态在 URL 单一来源，组件 ref 只是运行时镜像）、无台账数量变动，通过。
