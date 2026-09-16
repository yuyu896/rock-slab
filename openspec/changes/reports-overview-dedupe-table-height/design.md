# 报表总览去重复 + 表格定高 — 技术设计

## Context

`v-else` 兜底表格同时承接 overview/branch 两 tab；`.table-container` 无高度约束。

## Decisions

### D1：显式条件 + 总览瘦身

底部表格 `v-else` → `v-else-if="reportType === 'branch'"`——overview 不再命中（该 tab 无表格内容，指标卡+图表在 tabs-nav 之前的公共区，天然仍在）。branch 单独命中。

### D2：容器定高滚动

该表格容器加 `max-height: 560px; overflow-y: auto`；`thead th` 加 `position: sticky; top: 0; z-index: 1; background`（沿用既有 data-table sticky 模式）。仅作用于 branch 表（changeDetails/consumables/category 表格滚动行为后续按需，本次不动）。

## Risks / Trade-offs

（无——纯展示层）

## Migration Plan

随前端构建生效。

## Open Questions

（无）
