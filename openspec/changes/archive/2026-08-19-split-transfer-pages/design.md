## Context

当前侧边栏结构（MainLayout.vue navItems）：
```
资产管理 → 资产列表、采购入库、调拨记录
```
路由只有 `/assets/transfer` 一个，Transfer.vue 内通过 Tab 切换 6 种类型。

后端 API 已按 action_type 区分，前端 `getTransfers` 已支持 `type` 参数筛选。

## Goals / Non-Goals

**Goals:**
- 侧边栏"资产管理"下新增"资产流转"子分组，展开显示 6 种流转类型
- 每种流转类型有独立路由、独立页面组件、独立新建表单
- 复用现有 transfers API，不新增后端接口
- 原 Transfer.vue 保留为"全部流转"聚合视图（可选入口）

**Non-Goals:**
- 不修改后端 API
- 不修改移动端路由
- 不实现页面间共享组件抽取（后续优化）

## Decisions

1. **侧边栏结构调整** — 将"调拨记录"替换为"资产流转"分组，子菜单包含：采购入库、领用出库、归还、调拨、维修、报废
2. **路由设计** — `/transfers/purchase`、`/transfers/assign`、`/transfers/return`、`/transfers/transfer`、`/transfers/repair`、`/transfers/scrap`，原 `/assets/transfer` 重定向到 `/transfers/transfer`
3. **页面组件** — 每个页面从 Transfer.vue 提取对应逻辑，包含：列表表格、筛选栏、新建弹窗、详情弹窗、审批操作
4. **共享逻辑** — 使用 composable 函数（`useTransferList`）提取公共数据获取、审批、导出逻辑，避免每个页面重复代码
5. **新建弹窗** — 每个页面有独立的表单字段，不再通过 `createType` 条件渲染

## Risks / Trade-offs

- [6 个页面组件代码量较大] → 通过 composable 提取公共逻辑，每个页面仅定义差异部分
- [原路由 `/assets/transfer` 需兼容] → 添加 redirect 到新路由
