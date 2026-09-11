# 版宽统一 + 采购筛选 — 技术设计

## Context

版宽现状：transfer 三列表 1400px、回收单 1600px、回收台账 100%、盘点 1400px。采购列表筛选仅关键字+状态（无分公司）。BranchFilterSelect 组件与 toBranch filterset 均现成。

## Goals / Non-Goals

**Goals:** 五页版宽统一 1600px；采购列表补可搜索分公司筛选。

**Non-Goals:** 领用筛选（已有调出/调入）；非列表页与资产台账/实例档案版宽（用户未提）。

## Decisions

### D1：逐页一行样式改（不抽全局类）

五个页面各自的根容器样式改为 `max-width: 1600px; margin: 0 auto`（保持其余 flex 布局契约不动）。不抽公共 class——各页 scoped 样式独立、改动最小、无回归面。

### D2：采购筛选走 toBranch 口径

采购单分公司语义=入库方（调入分公司 to_branch）。PurchaseList 的 filters 加 `toBranch`（BranchFilterSelect），fetchTransfers 透传；useTransferList 的 filters 已有 toBranch 字段（调拨/领用在用）——采购列表此前未渲染控件而已，数据链路现成。

## Risks / Trade-offs

（无——样式一行 + 现成组件复用；vitest 守护采购筛选参数）

## Migration Plan

随前端构建生效。

## Open Questions

（无）
