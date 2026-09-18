# 勾选随筛选重置 — 技术设计

## Context

selectedIds 为页面级 Set，无任何重置路径；filters 已有 watch（翻页+fetch）。

## Decisions

### D1：filters watch 内清空

既有 `watch(filters, ...)` 回调首行加 `selectedIds.value = new Set()`——数据集即将切换，旧勾选失效。翻页不经 filters watch，天然保留。

## Risks / Trade-offs

（无——纯交互卫生）

## Migration Plan

随前端构建生效。

## Open Questions

（无）
