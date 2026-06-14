## Context

SidebarNav.vue 中"资产盘点"菜单项的角标值 `badge: 3` 是静态硬编码的。移动端 Home.vue 已有动态获取盘点任务数量的实现，使用 `getInventoryTasks({ status: 'pending,in_progress', pageSize: 1 })` 仅获取 count。

当前 navItems 是组件内的常量数组，无响应式数据源。

## Goals / Non-Goals

**Goals:**
- 角标实时反映 pending + in_progress 状态的盘点任务总数
- 仅在数量 > 0 时显示角标
- 复用现有 API，不引入新接口

**Non-Goals:**
- 不做轮询或 WebSocket 实时推送（组件挂载时获取一次即可）
- 不修改移动端导航（MobileLayout 中盘点 tab 无角标，保持现状）
- 不修改后端 API

## Decisions

**1. 数据获取方式：组件内直接调用 API**
- 在 SidebarNav 的 `onMounted` 中调用 `getInventoryTasks`，用 `ref` 存储计数
- 放弃方案：使用 Pinia store（inventory store 已有但未在 SidebarNav 使用，引入 store 会增加不必要的复杂度，因为这里只需要一个 count 值）
- 理由：与移动端 Home.vue 保持一致的轻量方式

**2. 角标显示逻辑：count > 0 时显示**
- 将 navItems 改为 computed 属性，动态计算 badge 值
- count 为 0 时不渲染角标元素

**3. 请求策略：pageSize=1 仅取 count**
- 使用 `pageSize: 1` 避免拉取不必要的数据，仅依赖响应中的 `count` 字段

## Risks / Trade-offs

- [API 请求延迟] → 在 `onMounted` 中发起请求，页面加载后角标短暂为空（无感知）
- [无实时更新] → 用户在当前会话中完成盘点后角标不会自动更新 → 可接受，切换页面或刷新即可同步
