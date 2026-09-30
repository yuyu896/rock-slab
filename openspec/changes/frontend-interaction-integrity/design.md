## Context

PermissionAssign.vue 以 `isAdminUser`（computed：**当前** `selectedUser.role === 'admin'`）短路四处 UI（勾选禁用/脏检查/保留计数/预览），而「保存后岗位」是 `selectedRole`（换岗 draft）——两者在降级流程中分裂。admin 运行时恒真、无 OperationGrant 行，`onPickRole` 的初始化又显式排除 admin 源用户，三处叠加成「降级即清零」。规范（position-appointment-permissions R「保存脏检查与只补不删」）的换岗初始化语义本就覆盖此场景。路由守卫（router/index.ts:110-123）同步读 `useUserStore().isAdmin/can()`，而 main.ts 的 `fetchProfile` 发起后不等待即 mount。TransferLinesEditor 的 `autoFillAmount` 仅在 `金额 === null` 时填一次。MobilePurchase 的类目响应判断 `Array.isArray(data) ? data : []`，后端 StandardPagination 返回 `{count, results}`。

## Goals / Non-Goals

**Goals:**

- admin 降级 = 正常换岗：勾选可用、初始化「模板 ∪ 既有」、可保存、结果含模板操作码
- 预览/计数/脏检查与保存后语义一致；组织名注入面消除
- 刷新管理路由不再误跳转（等待 profile，一次性成本）
- 四个交互 bug 修复

**Non-Goals:**

- 不改后端任何接口/权限模型（页面缺陷纯前端）
- 不做金额强制派生（用户手填金额仍可覆盖，只保护「未手改」的自动值）
- 不重做权限页布局

## Decisions

**1. admin 特权判定统一改 `selectedRole === 'admin'`（保存后口径），新增 computed `isAdminDraft` 命名表意。**
勾选禁用/脏检查/保留计数/范围预览四处同步替换；`onPickRole` 删除 `selectedUser.role !== 'admin'` 条件——规范要求换岗初始化为「模板 ∪ 既有」，admin 既有为空集，并集=模板集，恰是期望的降级初始态。选回 admin 模板时 `allOperations` 分支已不动勾选集，行为不变。

**2. 预览语义取保存后：`selectedRole === 'admin'` → 「全部（内置）」，否则按授权行拼装。**
顺带修 `.value` 解包缺失（该 bug 使所有用户看到「全部（内置）」）。

**3. XSS 用转义而非重构 DOM：`scopeLabel` 内组织名经 `esc()`（&<>"' 五字符），保留 `<strong>` 排版。**
改结构去 v-html 需重排模板；转义收敛注入面且改动最小。名称均来自 DB（Region/Branch/Team.name）。

**4. 守卫等待：store 增 `profileLoaded`（fetchProfile 成功置位），守卫在 `requiresAdmin`/`operation` 判定前 `await` 一次加载。**
只在此两类路由等待（普通页面不受影响、无额外延迟）；失败 catch 后走原重定向路径（无 token → login 的既有逻辑在前）。

**5. 金额联动：LineDraft 增可选 `金额Auto` 标志——自动填充/重算置 true，金额输入 @input 置 false；`onQtyChange`（采购）在 `单价非空 && 金额Auto` 时重算。**
手填保护与自动派生并存，语义清晰；编辑驳回单预填金额时同样标 false（非自动值）。

**6. 盘点按钮：`usePermission().canManageAssets` 显隐创建/删除/作废/开始，`can('approve_inventory')` 显隐审批；`/inventory/create` 路由补 `meta.operation: 'manage_assets'`。**
与 Category/Organization 页既有模式一致；后端 403 仍是二重兜底。

## Risks / Trade-offs

- [守卫 await 首次进入管理路由多等一个 profile 往返] — 无 token 时本就要等 login；有 token 时一次往返换正确性
- [金额Auto 标志在草稿序列化/还原时的存续] — 仅编辑会话内存态，不落库，无持久化需求

## Migration Plan

纯前端。部署即生效。验证：admin 用户在权限分配页换岗后勾选可用且预填模板集；普通用户预览不再显示「全部」；刷新 /admin/permissions 不跳转；采购改数量金额跟随；回收清品目不崩；移动采购类目有选项；无权用户不见盘点操作按钮。
