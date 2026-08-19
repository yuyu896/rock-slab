## 1. 资产流转新增弹窗改为路由页面

- [x] 1.1 将各流转类型的"新建表单字段定义与提交逻辑"整理为可被页面复用（沿用 `useTransferList(type)` 组合式函数，必要时抽出字段配置）
- [x] 1.2 新增 `views/transfers/PurchaseCreate.vue`（采购入库），字段与原 `PurchaseList` 模态一致
- [x] 1.3 新增 `views/transfers/AssignCreate.vue`（领用出库），字段含使用人、所属分公司等
- [x] 1.4 新增 `views/transfers/TransferCreate.vue`（调拨），保留"调出分公司≠调入分公司"校验
- [x] 1.5 新增 `views/transfers/RecoveryCreate.vue`（回收），字段含回收分类、规格型号等
- [x] 1.6 在 `router/index.ts` 增加 4 条 create 路由（如 `transfers/purchase/create`），挂在 `MainLayout` 下
- [x] 1.7 各 `*List.vue`（Purchase/Assign/Transfer/Recovery）移除 `showCreateModal` 模态及相关模板/样式，"新建"按钮改为 `router.push` 到对应 create 路由
- [x] 1.8 各 create 页提交成功后 `router.replace` 回列表并触发刷新；提供"取消"返回列表

## 2. 资产 / 固定资产新增改为路由页面

- [x] 2.1 将 `views/assets/AssetCreateForm.vue` 由 `modal-overlay` 子组件改造为路由页面（或新增 `AssetCreate.vue` 并迁移表单）
- [x] 2.2 将 `views/FixedAssetList.vue` 的 `el-dialog`（新增固定资产）抽离为 `FixedAssetCreate.vue` 路由页面
- [x] 2.3 在 `router/index.ts` 增加资产/固定资产 create 路由；对应列表页"新增"按钮改为跳转、移除原弹窗

## 3. 个人中心面板定位修复

- [x] 3.1 `components/layout/UserPanel.vue` 的 `.user-panel` 由 `position: absolute`(锚 `.sidebar-footer`) 改为 `position: fixed`，按触发按钮 `getBoundingClientRect()` 计算 `left`，`bottom` 锚定视口底部偏移
- [x] 3.2 面板 `max-height` 取 `calc(100vh - 2 * 间距)`、向上生长，内部 `overflow-y: auto`
- [x] 3.3 删除失效的 `adjustPanelPosition()`，改为面板打开时与 `window resize` 时重算并 clamp；卸载时移除监听
- [ ] 3.4 验证：在 1080p、短屏（如 768px 高）、改变窗口大小三种情况下，面板完整在视口内、底部按钮（修改密码/退出登录）可达

## 4. 修改密码流程修复

- [x] 4.1 `components/layout/PasswordChangeModal.vue` 捕获 `updatePassword` 响应，将返回的 `token` 写入 `localStorage('rock_slab_token')` 与 `userStore.token`（及 axios 默认头）后再展示成功、emit `done`
- [x] 4.2 错误分支改读 `e.response.data.detail`（或直接复用 `utils/request.ts` 的 `handleApiError`），不再读 `.message`
- [x] 4.3 合并 `api/users.ts` 与 `api/auth.ts` 中重复的 `updatePassword`，统一保留一处
- [ ] 4.4 验证：改密成功后保持登录、立即刷新列表不 401；原密码错误时显示真实原因

## 5. 登录乱码修复（UTF-8）

- [x] 5.1 `nginx/qhpanpan.top.conf` 的 443 `server` 块增加 `charset utf-8;` 与 `charset_types text/css text/xml text/plain application/json application/javascript image/svg+xml;`
- [ ] 5.2 在生产服务器 `curl -I` 验证 `/api/` JSON 响应是否带 `charset`；若缺失则评估对代理启用 `override_charset on`（注意双编码风险）
- [x] 5.3 `views/Login.vue` 手机号校验由 `/^\d{11}$/` 升级为 `/^1[3-9]\d{9}$/`，并保持中文提示为本地 UTF-8 字符串
- [ ] 5.4 验证：中文 Windows 客户端访问 `qhpanpan.top`，登录页无效手机号提示与全站中文均无乱码

## 6. 构建与端到端回归

- [x] 6.1 `cd frontend && npm run build` 通过类型检查与构建
- [x] 6.2 `cd frontend && npm run test` 前端单元测试通过
- [ ] 6.3 `nginx -t && nginx -s reload` 并核对响应头含 `charset=utf-8`
- [ ] 6.4 部署后逐项回归：4 类流转新增、资产/固定资产新增、个人中心短屏不溢出、改密保持登录、登录错误中文正常
