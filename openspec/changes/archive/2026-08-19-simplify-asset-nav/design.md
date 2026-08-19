## Context

当前 `MainLayout.vue` navItems 中"资产管理"是带 children 的分组项，但只有一个子项"资产列表"。

## Decisions

1. **移除 children** — 将"资产管理"改为无 children 的平级导航项，path 直接指向 `/assets/list`，icon 保持 `box`
2. **标签调整** — label 改为"资产列表"，更直观地反映页面内容

## Risks / Trade-offs

- 无风险，纯粹的 UI 简化操作
