# 列表筛选持久化与宽度均衡 — 技术设计

## Context

PC 列表页筛选态全部存于组件局部 `ref`（`useTransferList.ts:23` 及各页面自带），`MainLayout` 的 `<router-view />` 无 keep-alive，路由切换即销毁重建。筛选栏布局各页同构：`.filter-item.search { flex: 1 }` + `BranchFilterSelect` 固定 220px。用户高频痛点场景：审批采购入库 → 逐单进详情审批 → 返回 → 筛选归零。

## Goals / Non-Goals

**Goals:**

- 详情页往返后筛选与页码完整恢复；返回时数据重新拉取（新鲜）。
- 带 query 的 URL 直接进入对应筛选视图（可分享/收藏）。
- 筛选栏宽度在所有列表页观感均衡：搜索框 ≤400px、分公司下拉 300px。

**Non-Goals:**

- 不做 keep-alive 页面缓存（不保滚动位置；换来数据新鲜与实现简单）。
- 不改后端过滤接口与语义（`branch-filter` 等 spec 不动）。
- 不覆盖移动端（其列表无筛选态）。
- 不持久化排序等暂不存在的状态。

## Decisions

### D1：路由 query 为唯一持久层，运行时 ref 为镜像

新建 `useQueryFilters` composable，职责：

```
init:   从 route.query 反序列化为 filters 初值（数组型逗号分隔，如 ?toBranch=杭州,北京&page=2）
sync:   watch(filters) → 序列化写 route.query（router.replace，不产生历史记录）
skip:   初始化恢复期间置跳过标记，避免「恢复触发 watch → 重置 page=1 / 双重拉取」
reset:  手动重置按钮 → filters 归零（watch 自然清空 query）
```

理由：query 是浏览器原生状态容器——返回/刷新/分享免费获得；replace 不污染历史（后退不会逐条回放筛选变化）。
备选 Pinia/sessionStorage：刷新即丢或不可分享，且多一个状态源；备选 keep-alive：审批后回旧数据，需另做失效广播，复杂度更高。均弃。

### D2：`useTransferList` 内嵌接入，其余页面组合接入

- 流转四列表：`useTransferList` 内部调用 `useQueryFilters`（filters 定义集中在此，四页零改动即受益）。
- 自带 filters 的页面（`FixedAssetList`/`AssetSummary`/`Inventory`/`InventoryTaskList`/`AuditLog`/`RecoveryLedger` 及 `FilterPanel` 使用处）：声明式接入——把 filters 的初值函数与序列化键表传给 `useQueryFilters`，页面自身 fetch 时机不变（`onMounted` 在恢复后的 filters 上拉取）。

分批实施：先 `useTransferList` 四页（用户痛点场景）+ `FixedAssetList`，其余页面第二批，降低一次回归面。

### D3：宽度统一走两处全局改点

- `BranchFilterSelect.vue`：`.branch-filter-select { width: 220px }` → `300px`——所有使用处（含 `AdjustRecordsDialog` 弹窗）自动生效。
- 各列表页 `.filter-item.search`：加 `max-width: 400px`（flex:1 保留，窄屏仍自适应收窄）。
- 不新建共享样式文件（各页 filter CSS 本就复制式同构，改点机械）。

## Risks / Trade-offs

- [恢复期 watch 误触发（双拉/页码重置）] → D1 的 skip 标记 + 单测覆盖「带 query 挂载仅拉取一次、页码保持」。
- [query 键冲突/脏值] → 未知键忽略、反序列化失败回退默认值；各页键名沿用 API 参数名（status/keyword/fromBranch/toBranch/branch/page）。
- [URL 变长] → 仅在有值时写键，空值键删除；多选分公司逗号分隔可接受。
- [router.replace 频繁调用] → 输入搜索 debounce 已存在（keyword 请求侧）；query 写入随 watch 自然节流，必要时 nextTick 合并。

## Migration Plan

纯前端，随常规发版；无迁移无回滚风险。上线后用户既往习惯（重选筛选）不受影响，query 为可选增强。

## Open Questions

（无——范围、方案、宽度三项已与用户确认：全部列表页 / 路由 query / 搜索限宽+分公司加宽 300。）
