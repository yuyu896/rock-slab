# 报表三修 — 技术设计

## Context

by_branch 后端固定 -stock 序；by-status 已有（图表用）；transferDetails 前端拉单据明细。

## Decisions

### D1：前端 computed 排序（排行）

`sortedBranchStats = computed(() => [...branchStats].sort((a,b) => metric(b) - metric(a)))`——图表与导出共用；后端不动。

### D2：总览状态表复用 by-status 数据

statusRes 已在总览拉取（categoryDistribution）。新增状态汇总表（行=在库/在用/回收库，列=数量/占比），纯前端组装；容器复用 branch-table-wrap 定高滚动样式。

### D3：后端聚合端点 changes-by-item

`GET /api/reports/changes-by-item/?range=month|quarter|year`：生效单据明细行按品目聚合——values(item, item__asset_code, item__asset_name, item__unit, transfer__action_type).annotate(qty=Sum('数量'))，行转列为 入库/领用/归还/调拨/回收。数据范围与 scope 一致；时间过滤同既有 overview 口径。

### D4：前端变动 tab 换表

transferDetails 保留（导出 fallback 不再需要——导出改聚合口径）；表列：品目编号/名称/单位/入库/领用/归还/调拨/回收；定高滚动复用样式。

## Risks / Trade-offs

- [聚合丢失单据可溯性] — 单据列表/详情仍可查（非目标内说明）
- [by-status 占比分母] — 总量=三态和，回收库占比同口径

## Migration Plan

后端新端点随部署；前端构建生效。

## Open Questions

（无）
