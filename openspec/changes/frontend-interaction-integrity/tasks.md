## 1. 权限分配页

- [x] 1.1 新增 `isAdminDraft`（selectedRole==='admin'）替换四处判定：勾选禁用（模板 63 行）、opsDirty、keptExtraCount、previewScopeText（顺带修 `.value` 解包，语义取保存后岗位）
- [x] 1.2 `onPickRole` 删除 admin 源用户排除条件（换岗初始化对 admin 降级同样生效）
- [x] 1.3 `scopeLabel` 组织名过 `esc()` 转义（v-html 注入面消除）

## 2. 守卫与交互

- [x] 2.1 `store/user.ts` 增 `profileLoaded`；`router/index.ts` 守卫 async 化（requiresAdmin/operation 判定前 await 一次加载）
- [x] 2.2 `TransferLinesEditor`：LineDraft 增 `金额Auto`，数量/单价变化时重算未手改的自动值；`onItemPicked` 空品目守卫
- [x] 2.3 `MobilePurchase` 类目响应兼容 `{count,results}`；`InventoryTaskList` 按钮权限显隐 + `/inventory/create` 路由 `meta.operation`

## 3. 验证

- [x] 3.1 vitest 全跑 + `npm run build`
- [ ] 3.2 手验要点记录（admin 降级流程/预览/刷新管理页/金额联动/回收清品目/移动类目/盘点按钮）

> 手验要点：admin 用户在权限分配页换岗后勾选可用且预填模板集、保存后非零权限；普通用户范围预览不再显示「全部（内置）」；刷新 /admin/permissions 不再弹回；采购改数量金额跟随（手改过的不跟）；回收单清空品目不报错；移动端采购类目下拉有选项；无权用户不见盘点创建/操作按钮。既有用例「手填不覆盖」按新契约更新（自动值跟随、手填停跟）。
