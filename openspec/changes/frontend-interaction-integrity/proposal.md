## Why

中风险第二批（权限页与交互完整性）：① 权限分配页对 admin 用户的**降级流程**违背「只补不删」规范——勾选框按当前岗位禁用（保存前恒禁）、换岗初始化排除 admin 源用户（admin 无授权记录 → 初始化为空）、脏检查与保留计数都按当前岗位短路，结果是 admin 降级保存后**操作权限清零**且操作者全程无法勾选；② 「若保存后的范围」预览里 `isAdminUser` 是 ComputedRef 未解包，恒为真 → 任何用户都显示「全部（内置）」；③ 组织名称裸拼 HTML 进 `v-html`（存储型 XSS）；④ 管理路由刷新误跳转——`fetchProfile` 不 await，守卫先于用户信息加载执行；⑤ 四个交互 bug：采购金额不随数量重算（仅首次为空时自动填）、回收单清空品目点击崩溃（`null.asset_code`）、移动端采购类目下拉读不了分页响应恒空、盘点任务页按钮无权限显隐。

## What Changes

- 权限分配页的 admin 特权判定（勾选禁用/脏检查/保留计数/范围预览）一律改为基于**保存后岗位**（selectedRole）：降级到非 admin 时勾选可用、按「模板 ∪ 既有」初始化（admin 既有为空即模板集，与规范口径一致）
- 范围预览 `isAdminUser` 解包修正，语义取「保存后仍为 admin 才显示内置全量」
- `scopeLabel` 输出的组织名过 HTML 转义（保留 `<strong>` 排版，消灭注入面）
- 路由守卫 async 化：`requiresAdmin`/`operation` 判定前等 `fetchProfile` 完成（store 增 `profileLoaded` 标志，一次加载后续导航零开销）
- 采购行金额自动值跟踪：数量变化时若金额仍为自动计算值（未被手改）则重算；手动编辑金额后不再覆盖
- 回收单 `onItemPicked` 空品目守卫；移动端类目下拉兼容 `{count,results}` 分页响应；盘点任务页创建/行操作按钮按 `manage_assets`（审批按 `approve_inventory`）显隐，创建路由补 `meta.operation` 兜底

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `position-appointment-permissions`: 「保存脏检查与只补不删」要求补齐 admin 降级场景（按保存后岗位判定）；新增范围预览正确性与组织名转义要求
- `frontend-contract-alignment`: 新增守卫等待 profile、采购金额联动、分页响应兼容、盘点入口权限显隐四项交互契约

## Impact

- `frontend/src/views/admin/PermissionAssign.vue`（判定口径/解包/转义）
- `frontend/src/router/index.ts` + `src/store/user.ts`（守卫等待）
- `frontend/src/views/transfers/components/TransferLinesEditor.vue`（金额联动/空品目守卫）
- `frontend/src/views/mobile/MobilePurchase.vue`（分页兼容）
- `frontend/src/views/inventory/InventoryTaskList.vue` + 路由（权限显隐）
- vitest + `npm run build` 门禁；无后端改动（除路由 meta 前端侧）
