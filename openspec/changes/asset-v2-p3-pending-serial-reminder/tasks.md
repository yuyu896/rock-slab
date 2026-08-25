## 1. 实施

- [x] 1.1 `SidebarNav.vue`：`nav-submenu-item` 模板补徽标 span（复用 `.nav-badge` 样式，仅 badge 存在且非收起态渲染）
- [x] 1.2 `SidebarNav.vue`：onMounted 调 `getFixedAssets({ pending_serial: '1', pageSize: 1 })` 取 count 存 `pendingSerialCount`（失败 catch 置 0），挂到"实例档案"子项 badge（>0 才挂）

## 2. 测试与验收

- [x] 2.1 vitest：count>0 徽标显示且数字正确；count=0/接口失败不显示；请求参数含 `pending_serial: '1'`
- [x] 2.2 全量验收：前端 vitest 全绿、`npm run build` 通过、后端 pytest 全绿（确认零改动无回归）
