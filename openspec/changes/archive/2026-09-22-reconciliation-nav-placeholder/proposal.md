## Why

集团租赁电脑/手机每月需按供应商账单核对实例序列号（双方匹配/仅系统有/仅账单有），该功能为**大变动，另行专门立项**；本期按用户定案仅把导航模块占上位——页面空白，功能后续以专门提案填充。

## What Changes

- 新增顶级导航项**「对账」**（占位期仅 admin 可见），位于「资产盘点」与「组织架构」之间
- 新增路由 `/reconciliation`（requiresAdmin）与空白占位页（仅标题，无内容无操作）
- 无任何后端改动、无业务逻辑

## Capabilities

### New Capabilities

- `reconciliation`: 对账模块的导航入口与占位页（业务功能——账单导入/序列号比对/差异处理——由后续专门提案以 MODIFIED/ADDED 扩充本 capability）

### Modified Capabilities

（无）

## Impact

- 前端：`router/index.ts`（+1 路由）、`SidebarNav.vue`（+1 admin 条件菜单项 +1 图标）、新增 `views/Reconciliation.vue`（空白占位）
- 后端：零改动
- 防误伤边界：三个纯新增文件/片段，不触碰任何既有组件与逻辑；非 admin 不可见且路由守卫拦截
- 名称/位置/可见性为本提案默认口径（探讨会建议值），评审时可改，功能立项时最终定
