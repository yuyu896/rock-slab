# 报表总览去重复 + 分公司表格定高

## Why

统计报表「资产总览」与「分公司报表」两 tab 底部渲染同一张 `branchStats` 表（模板 v-else 兜底同时承接两 tab），内容完全重复；且表格容器无高度上限，72 家分公司整页铺开拖长页面（第 33 案只修了图表卡片，表格未覆盖）。

## What Changes

- 「资产总览」tab：移除底部分公司表格——指标卡（总资产/总值/活跃率/库存不足）+ 图表（分公司排行/分类分布）即总览内容
- 「分公司报表」tab：表格保留，改为 `v-else-if reportType === 'branch'` 显式条件；容器定高（max-height 560px）+ 内部滚动 + 表头 sticky 常驻
- 非目标：导出逻辑不动（分公司报表导出仍可用）；图表区（已定高）不动

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `report-metrics`: 资产总览去重复；分公司报表表格定高滚动

## Impact

- **前端**: 仅 `Reports.vue`（tab 条件 + 表格容器样式）
