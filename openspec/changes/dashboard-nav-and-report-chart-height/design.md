# 工作台跳转 + 图表定高 — 技术设计

## Context

`goToPendingApprovals` push `/assets/transfer`（旧路由 redirect 调拨）。Reports 图表卡片无高度约束。

## Decisions

### D1：跳转带 query + 列表页初始化

Dashboard：`router.push({ path: '/transfers/purchase', query: { status: '待审批' } })`。PurchaseList filters 初始化读 `route.query.status`（沿用 FixedAssetList 读 keyword 的既有模式）；侧栏无感。

### D2：chart-card 定高滚动

`.chart-card { max-height: 480px; display: flex; flex-direction: column }`；`.chart-header { flex-shrink: 0 }`；`.chart-body { overflow-y: auto; min-height: 0 }`。标题常驻、内容滚动；单卡数据少时高度自适应不受影响。

## Risks / Trade-offs

- [趋势图/状态分布卡片是否受影响] —— 通用样式对全部 chart-card 生效，数据少的卡片不受 max-height 影响；趋势图条形高度为百分比不受限
- [移动端] —— 单列布局同样适用

## Migration Plan

纯前端，随构建生效。

## Open Questions

（无）
