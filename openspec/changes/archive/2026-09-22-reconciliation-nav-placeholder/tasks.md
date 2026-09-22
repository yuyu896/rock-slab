## 1. 前端占位

- [x] 1.1 `router/index.ts`：新增 `/reconciliation` 路由（requiresAdmin，懒加载 Reconciliation.vue，title 对账）
- [x] 1.2 `SidebarNav.vue`：admin 条件渲染顶级项「对账」（资产盘点与组织架构之间）；icons 表新增 reconcile 图标
- [x] 1.3 新增 `views/Reconciliation.vue`：空白占位页（仅标题）

## 2. 验证收尾

- [x] 2.1 `npm run build` + vitest 全量通过
- [x] 2.2 拆 feat + openspec 两 commit，push
- [x] 2.3 手验：admin 见入口进空白页；普通账号不见入口、URL 直达被重定向（2026-09-22 用户验证通过）
