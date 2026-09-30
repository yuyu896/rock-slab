## ADDED Requirements

### Requirement: 守卫权限判定必须等待用户信息就绪

路由守卫对 `requiresAdmin` / `meta.operation` 路由的权限判定 MUST 在用户信息（profile 与操作码集）就绪后进行：未就绪时 MUST 先等待加载完成（一次性，加载成功后后续导航零等待）再判定，避免直接刷新管理类路由时因空 profile 被误重定向到 dashboard。加载失败时按既有无凭证路径处理（登录页/默认跳转），不得阻塞路由系统。

#### Scenario: 刷新管理路由不误跳

- **WHEN** 已登录的管理员直接刷新 `/admin/permissions` 页面
- **THEN** 守卫等待 profile 加载完成，页面正常进入（不被弹回 dashboard）

#### Scenario: 普通页面无额外等待

- **WHEN** 用户信息已加载后导航任意路由
- **THEN** 守卫不再发起等待，导航行为与现状一致

### Requirement: 建单与列表页交互基础契约

采购明细行的金额自动值 MUST 跟随数量联动：金额为自动计算值（未被手动修改）时，数量或单价变化 MUST 重算金额；手动修改过金额的行 MUST NOT 被自动覆盖。品目选择器清空回调 MUST 空值安全（不得对 null 品目访问属性）。下拉数据源 MUST 兼容后端 StandardPagination 分页响应（`{count, results}`）与裸数组两种形态。盘点任务页的创建/删除/作废/开始入口 MUST 按 `manage_assets` 授权显隐、审批入口按 `approve_inventory` 显隐，创建路由 MUST 以 `meta.operation` 做 URL 直达兜底（后端 API 权限仍是二重校验）。

#### Scenario: 采购金额跟随数量

- **WHEN** 采购行已自动填入金额（单价×数量）后修改数量
- **THEN** 金额重算为新单价×新数量；手动改过金额的行不受影响

#### Scenario: 清空品目不崩溃

- **WHEN** 回收单明细行的品目被清空
- **THEN** 行数据安全重置，页面无报错

#### Scenario: 移动端采购类目可选

- **WHEN** 打开移动端采购建单页
- **THEN** 类目下拉列出后端返回的全部类目（分页响应被正确读取）

#### Scenario: 无权用户不见盘点操作

- **WHEN** 不持 `manage_assets` 的用户打开盘点任务页
- **THEN** 不出现「创建盘点任务」与删除/作废/开始按钮；直接访问创建路由被守卫拦回
