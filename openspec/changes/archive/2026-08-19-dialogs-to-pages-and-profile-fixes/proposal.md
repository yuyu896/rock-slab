## Why

当前前端有四个相互独立、但都直接影响日常使用的问题，集中在"新增"流程与个人中心：

1. 资产流转的新增操作（采购入库、领用出库、调拨、回收）以及新增固定资产/资产，全部以内嵌模态弹窗实现。表单字段多、空间局促，窄屏和移动端几乎无法填写，且弹窗遮挡列表上下文。
2. 左下角"个人中心"弹窗（`UserPanel.vue`）在任何屏幕尺寸下都向下溢出可视区域，底部的修改密码、退出登录等按钮被裁切、不可点击。
3. 个人中心"修改密码"看似失败——实际后端已改密并**轮换了 Token**，但前端丢弃了返回的新 Token，下一次请求即 401 跳回登录页，给用户"改密失败/被踢下线"的错觉。
4. 生产环境下，登录页手机号输入错误时，后端返回的中文错误信息被浏览器按 GBK 解码，显示为乱码（根因：`nginx/qhpanpan.top.conf` 全程未声明 `charset`）。

## What Changes

- **新增弹窗改为独立路由页面**：保留列表页"新建"按钮，但改为路由跳转到独立的 create 页面，提交后返回列表。
  - 资产流转：新增采购入库、新增领用出库、新增调拨、新增回收（`PurchaseList` / `AssignList` / `TransferList` / `RecoveryList` 中的 `showCreateModal` 模态）
  - 资产：新增固定资产（`FixedAssetList` 的 `el-dialog`）、新增资产（`AssetCreateForm` 的 `modal-overlay`）
  - **不在本次范围**：批量导入弹窗（`*ImportDialog`）、打印弹窗、详情/编辑抽屉
- **重构个人中心面板定位**（`UserPanel.vue`）：移除会失效的 `bottom: 0` + `adjustPanelPosition` JS 修补，改为基于视口的稳定定位、按可用高度动态限高、补齐 `resize` 监听与短屏适配，保证面板在任何屏幕都完整落在可视区域内。
- **修复修改密码流程**（`PasswordChangeModal.vue`）：响应成功后用返回的新 Token 同步更新 `localStorage` 与 Pinia `userStore`，再关闭弹窗；错误信息读取 `e.response.data.detail`（与 `handleApiError` 一致）而非 `.message`。
- **消除中文乱码**：Nginx 增加 `charset utf-8;`（作用于 `/api/` 代理与所有静态资源）；登录页前端补强手机号前缀校验，减少依赖后端错误回显。

## Capabilities

### New Capabilities
- `transfer-create-pages`: 资产流转（采购入库/领用出库/调拨/回收）及资产（固定资产/资产）的新增操作以独立路由页面承载，而非模态弹窗
- `user-panel-positioning`: 个人中心面板在任意屏幕尺寸（含短屏、移动端）下完整、稳定地显示在可视区域内，不溢出
- `account-password-change`: 用户在个人中心修改密码后保持登录态（消费新 Token），且错误信息正确展示
- `response-charset-utf8`: 所有 HTTP 响应（接口代理与静态资源）声明 UTF-8 字符集，中文不出现乱码（以登录页手机号错误提示为验收点）

### Modified Capabilities
<!-- 无现有 spec 的需求层级发生变化 -->

## Impact

- **前端**:
  - 路由：`router/index.ts` 新增 create 页面路由（如 `transfers/purchase/create`）
  - 新增页面组件：从各 `*List.vue` 抽离新建表单为 `*Create.vue`，列表页"新建"按钮改为 `router.push`
  - `components/layout/UserPanel.vue`、`components/layout/PasswordChangeModal.vue`、`layouts/MainLayout.vue`
  - `views/Login.vue`（手机号前缀校验）、`utils/request.ts`（错误字段统一）
- **后端**: 无接口契约变更——修改密码接口 `PUT /api/auth/password/` 已返回新 `token`，前端此前未消费
- **运维 / Nginx**: `nginx/qhpanpan.top.conf` 增加 `charset utf-8;`，需 `nginx -s reload`
- **回归验收**: 各新增页面表单提交与取消、修改密码后保持登录、登录错误提示中文正常、个人中心在 1080p / 短屏 / 移动端均不溢出
