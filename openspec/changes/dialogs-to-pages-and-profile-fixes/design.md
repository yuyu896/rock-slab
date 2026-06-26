## Context

本变更修复前端四个相互独立的问题，均围绕"新增流程"与"个人中心"：

- **新增即弹窗**：`PurchaseList` / `AssignList` / `TransferList` / `RecoveryList` 用自建 `modal-overlay` 承载新建表单（`showCreateModal`），`FixedAssetList` 用 `el-dialog`，`AssetCreateForm` 用 `modal-overlay`。其中 `TransferList` 表单多达 12 个字段，弹窗空间局促，窄屏/移动端几乎无法填写。
- **个人中心溢出**：`UserPanel.vue` 的 `.user-panel` 以 `position: absolute` 锚定在 `.sidebar-footer`（`bottom: 0; max-height: 80vh`），并有一个会失效的 `adjustPanelPosition()` JS 修补（在 footer 坐标系里设 `top:0`，对短屏无效）。`.sidebar-footer` 本身贴在视口底部，导致面板向下溢出、底部按钮不可达。
- **改密失败错觉**：`PUT /api/auth/password/` 后端在改密成功后**删除旧 Token、签发新 Token** 并在响应体返回 `{ detail, token }`；但 `PasswordChangeModal.vue` 丢弃响应、不更新 `localStorage('rock_slab_token')` 与 Pinia store，下一次请求即 401 跳登录。错误处理还读了不存在的 `e.response.data.message`（后端返回的是 `detail`），导致失败原因被吞掉。
- **登录乱码**：`nginx/qhpanpan.top.conf` 全程无 `charset` 指令，`/api/` 代理块与静态资源均未声明字符集；中国 Windows 客户端在响应缺少 `charset` 时按 GBK 解码 UTF-8 字节 → 乱码。表现最明显的是登录页手机号格式被后端拒绝时回显的中文错误（前端 `/^\d{11}$/` 只校验位数，无效但 11 位的号码会走到后端 `validate_phone`）。

约束：后端无接口契约变更（改密接口已返回 token）；生产由 Nginx 前置、共享 PG/Redis；移动端走独立 `MobileLayout`。

## Goals / Non-Goals

**Goals:**
- 所有"新增内容"表单改为独立路由页面，列表页"新建"按钮改为跳转，提交后返回列表并刷新。
- 个人中心面板在任意屏幕（含短屏、折叠侧栏）都完整落在视口内，底部按钮可达。
- 改密成功后用户保持登录（消费新 Token），失败时展示真实原因。
- 全站 HTTP 响应声明 UTF-8，登录页及全局中文不再乱码。

**Non-Goals:**
- 不改造批量导入弹窗（`*ImportDialog`）、打印弹窗、详情/编辑抽屉。
- 不重构移动端（`MobileLayout`）的新建流程——移动端已有 `MobilePurchase` / `MobileAssign` / `MobileTransfer`。
- 不变更后端 API 契约或数据模型。
- 不做"弹窗 vs 页面"的统一抽象框架——按现有 app 结构逐个迁移即可。

## Decisions

### 决策 1：新增表单抽离为独立 `*Create.vue` 路由页面（问题 1）
- **做法**：每个流转类型新增 `views/transfers/*Create.vue`，复用现有 `useTransferList(type)` 组合式函数的提交逻辑与字段定义；`router/index.ts` 增加 `transfers/<type>/create` 路由。列表页"新建"按钮由 `openCreateModal()` 改为 `router.push({ name: 'transferCreate', params: {...} })`。提交成功后 `router.replace` 回列表并触发刷新（通过路由 query 或返回后重新拉取）。固定资产/资产同理（`FixedAssetCreate.vue` / 改造 `AssetCreateForm` 为路由页）。
- **理由**：多字段表单需要完整视口与移动端可用性；路由页面可深链/书签、不遮挡列表上下文、天然支持浏览器后退。
- **备选**：`el-drawer` 侧抽屉——宽度仍受限、且与个人中心面板同病（溢出风险）；加大宽度 `el-dialog`——仍覆盖列表、移动端体验差。二者都不如路由页面。
- **复用**：表单字段定义集中到 `useTransferList`，列表页与新建页共享，避免重复。

### 决策 2：个人中心面板改为视口锚定的稳定定位（问题 2）
- **做法**：`.user-panel` 改为 `position: fixed`，以触发按钮位置计算 `left`，`bottom` 锚定视口底部偏移；`max-height` 取 `calc(100vh - 2 * 间距)`，面板向上生长，物理上不可能向下溢出。删除失效的 `adjustPanelPosition()`，改在 `open` 时与 `window resize` 时按 `getBoundingClientRect()` 重算并 clamp。
- **理由**：`fixed` 相对视口，与 footer 高度、侧栏折叠状态解耦；动态 `max-height` 保证面板始终装得下。
- **备选**：迁移到 `el-popover`（自带 flip/clamp）——但现有面板有定制样式/动画，改写量大，收益不明确，暂不采用。
- **移动端**：`<768px` 时侧栏 `translateX(-100%)` 隐藏，个人中心入口在 PC 布局不可达，移动端走 `MobileLayout`，故 PC 面板的 fixed 定位不影响移动端。

### 决策 3：改密消费新 Token + 错误字段对齐（问题 3）
- **做法**：`PasswordChangeModal.vue` 捕获 `updatePassword` 响应，将 `token` 写入 `localStorage('rock_slab_token')` 与 `userStore.token`（及 axios 默认头）后，再展示成功、emit `done`。错误分支改读 `e.response.data.detail`（或直接复用 `request.ts` 的 `handleApiError`）。
- **理由**：后端已返回新 Token，前端只是此前未消费；零后端改动、修复彻底。
- **清理**：`updatePassword` 在 `api/users.ts` 与 `api/auth.ts` 各有一份，统一保留一处，消除歧义。

### 决策 4：Nginx 声明 UTF-8 + 前端校验前置（问题 4）
- **做法**：
  1. `nginx/qhpanpan.top.conf` 在 `server`（443）块加 `charset utf-8;` 与 `charset_types text/css text/xml text/plain application/json application/javascript image/svg+xml;`，覆盖静态资源与 SPA 入口；确认 `/api/` 代理透传上游 `Content-Type`（DRF `CamelCaseJSONRenderer` 自带 `charset=UTF-8`）。
  2. 登录页前端校验从 `/^\d{11}$/` 升级为合法手机号正则（如 `/^1[3-9]\d{9}$/`），与 `validate-user-phone-format` 的精神一致，把更多无效输入拦在前端、减少依赖后端错误回显。
- **理由**：`charset utf-8;` 从源头杜绝静态资源乱码；手机号前置校验减少触发后端回显的路径。
- **备选**：对 `/api/` 用 `override_charset on` 强制改写——仅在确认上游缺 charset 时才需要，且可能双编码，默认不启用（见开放问题）。

## Risks / Trade-offs

- [用户习惯：弹窗 → 页面带来交互变化] → 保留"新建"按钮原位置，提交后自动返回并刷新列表，降低陌生感。
- [个人中心 fixed 定位在极端短屏仍可能偏高] → 动态 `max-height` + 内部 `overflow-y:auto` 保证可滚动可达，不会裁切按钮。
- [改密瞬间有并发请求持有旧 Token → 401] → 同步刷新 Token 后再关弹窗；改密为低频用户主动操作，可接受。
- [Nginx `override_charset` 误用导致双重编码] → 默认不启用，仅 `charset utf-8;`；是否需要 `override_charset` 由生产 `curl -I` 验证后决定。
- [路由页面增多、需维护返回逻辑] → 统一"提交成功 replace 回列表"约定，避免历史栈淤积。

## Migration Plan

1. **前端**（增量、可灰度）：新增 create 路由与 `*Create.vue`；列表页按钮改跳转；移除旧 `showCreateModal` 模态。`UserPanel.vue` / `PasswordChangeModal.vue` / `Login.vue` 改动为就地替换。
2. **Nginx**：编辑 `nginx/qhpanpan.top.conf` 增加 `charset utf-8;` + `charset_types`，`nginx -t && nginx -s reload`。回滚：还原配置 + reload。
3. **后端**：无变更，无迁移。
4. **验证**：构建前端（`npm run build`）→ 部署 → 逐项回归（见 tasks）。

## Open Questions

- 生产 `/api/` 响应是否真的缺少 `charset`？需在服务器 `curl -I -H 'Accept: application/json' https://qhpanpan.top/api/...` 确认，以决定是否对代理启用 `override_charset`。
- 新建页面是否需要共享一个 `TransferCreateLayout` 外壳？当前建议每类型独立组件 + 共享 `useTransferList`，待实现时评估。
