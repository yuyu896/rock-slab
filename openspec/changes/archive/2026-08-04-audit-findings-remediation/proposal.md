## Why

一次覆盖安全 / 后端 / 前端的全面审查发现：尽管读路径有 `DataScopeMixin` 兜底，**写路径普遍缺少权限声明与目标资源范围校验**，叠加用户管理接口的密码处理缺陷、盘点状态机并发漏洞、以及多处前端字段/URL 与后端契约脱钩的功能性 Bug。这些问题中既有**可被直接利用的越权 / 提权路径**，也有**用户日常使用会直接踩到的功能异常**（删除失效、盘点报告列空白、资产详情张冠李戴），且部分（如账号接管）已在生产环境可达，现在就应集中修复。

本提案聚焦 `remediate-audit-findings` **未覆盖**的新发现；与其重叠的两项（口令安全、并发控制）以 *Modified Capability* 形式扩展其尚未落地的需求，不重复造轮子。

## What Changes

> 每条标注「→ 引起什么问题」。严重度：**P0** 安全红线 / **P1** 数据一致性与功能 Bug / **P2** 健壮性与卫生。

### P0 — 安全红线（越权 / 提权 / 账号接管）

- **用户密码 update 路径未哈希** → 账号接管 / 提权。`UserSerializer` 只重写 `create` 未重写 `update`，`PATCH /api/users/{id}/` 带 `password` 走 ModelSerializer 默认 `setattr`，不经 `set_password()`。攻击者提交本地预生成的有效哈希（`make_password('xxx')`），即可在 `manage_users` 授权范围内接管任意账号；若范围内存在更高权限账号则直接**提权到 admin**。修复：`update` 重写为 `set_password`，或 `password` 不进 update 序列化器，密码变更一律走 `/api/auth/password/`。
- ~~**流转 / 资产写 action 漏权限声明**~~ **[实施时纠正]** 经 `test_rbac_matrix` 核实：业务发起（流转 purchase/assign/return/transfer/recovery、资产 create）对所有登录用户开放是**产品设计**（员工申请领用 / 采购 / 登记资产），非漏洞；仅 `import_excel` 等敏感写补声明 `manage_assets`。真正越权由下一条「写操作不校验目标分公司范围」防护。
- **写操作不校验目标分公司范围** → 跨区域篡改资产库存。`Transfer._create_action`、`InventoryTask.perform_create` 不校验 `from_branch/to_branch/branch` 是否在 `resolve_user_scope(user)` 内，区域 A 的 manager 可把区域 B 资产"调拨"到区域 C。修复：写前做 scope 校验，不在范围返回 400。
- **盘点 `check` 接口 IDOR** → 篡改跨范围资产库存。`check` 提交的 `asset_id` 用 `Asset.objects.get()` 全局取，不校验 `asset.branch == task.branch`，审批通过后 `_adjust_inventory` 会改这条资产库存。修复：asset 查询加 `branch=task.branch` 约束。
- **用户列表全量返回** → 手机号（= 登录账号）大批量泄露。`UserViewSet.list/retrieve` 返回全公司用户含 `phone`，且 `pagination_class=None`，任意登录用户一次拉全——为上面账号接管挑选目标提供便利，本身也是 PII 泄露。修复：list/retrieve 走 `_get_user_queryset`。
- **新建用户默认弱口令 `123456`** → 撞库登录。`UserSerializer.create` 未传密码默认 `'123456'` 且不走 `AUTH_PASSWORD_VALIDATORS`（`remediate-audit-findings` 4.1 未落地）。修复：未传密码返回 400 或生成随机密码 + 强制首登改密 + `validate_password`。

### P1 — 数据一致性 / 合规

- **盘点 `approve` 并发双扣库存** → 账实严重不符。`approve` 的 `get_object()` + `can_transition()` 均无锁，`_adjust_inventory` 只锁 asset 不锁 task；两个并发审批都过状态校验，diff 各应用一次（expected=10/actual=8 → 资产被扣到 6）。盘点其余状态转换（start/submit/reject/cancel/recount）同样缺锁。修复：`approve` 内 `select_for_update` 锁 task + 二次状态校验；状态机转换统一 `transaction.atomic`。
- **停用账号 Token 不失效** → 离职员工 30 天内仍可调 API。登录用 `status`，认证用 `is_active`，二者未联动；`status='inactive'` 不删 `ExpiringToken`。修复：停用时同步 `is_active=False` 并删除其 Token，或认证层额外校验 `status`。
- **改密不写审计日志** → 合规审计破洞。`audit_log` 装饰器假设 `args[0]` 是 ViewSet 的 `self`，对函数视图（`change_password_view`）`args[0]` 是 request，导致 `request=None`、审计静默失效。修复：装饰器兼容 FBV 与 ViewSet 两种调用。
- **通知向跨范围用户推送业务明细** → 数据泄露。`notifications/signals.py` 的 `get_approvers_for_branch` 实际不按 branch 过滤，直接返回全量 admin/director/manager/supervisor，通知体带资产名/编号/调出调入分公司，区域 A 的 manager 会收到区域 B 的调拨详情。修复：按 `resolve_user_scope` 反查对 `调出分公司` 有授权的用户，仅通知/抄送给他们。
- **Transfer `assign` 审批 TOCTOU** → 超发。库存是否足够的检查用无锁 fetch，与 `_sync_asset` 内的 select_for_update 是两次 fetch，并发可扣成负数被 `max(0)` 截断，实际发出多于账面。修复：库存校验并入 `_sync_asset` 事务。

### P1 — 前端功能性 Bug（用户直接感知）

- **盘点删除 URL 缺 `/api` 前缀** → 删除功能失效。`store/inventory.ts` 直接 `request.delete('/inventories/${id}')` 绕过封装，baseURL 为空，请求不命中代理，用户点删除无反应。修复：改用已有的 `deleteInventoryTask(id)` 封装。
- **盘点报告"资产编号/名称"两列全空** → 无法核对实物。前端渲染 `assetId/assetName`，后端 `InventoryItemSerializer` 只暴露 `asset`（FK 主键）。修复：后端补 `asset_code/asset_name`，前端渲染对齐。
- **资产详情抽屉显示全公司最近 50 条流转** → 严重误导。`AssetList.viewDetail` 调 `getTransfers({pageSize:50})` 未按资产过滤，后端 `TransferFilterSet` 也无资产编号过滤器。修复：后端加 `资产编号` 过滤器，前端按当前资产过滤。
- **MobileScan 任务分公司字段读错 key** → 手机端分公司恒空。读 `branchId`，后端返回 `branch`。修复：改读 `branch`。
- **资产列表"快捷筛选"失效、批量调拨死按钮、通知中心"查看全部"路由不存在、NotificationCenter 全局 click 监听未解绑（内存泄漏）** → 半成品入口未接后端或路由缺失。

### P2 — 健壮性 / 性能 / 卫生

- **前端 3 个超大 chunk** → 首屏加载慢。`element-plus` 881KB、`exceljs` 940KB、`xlsx` 429KB，建议动态 `import()` 懒加载。
- **FixedAsset API 完全 `any` 化、`formatMoney` 不处理 decimal 字符串** → 类型保护为零、金额格式异常（DRF DecimalField 序列化为 `"99.50"` 字符串，`String.toLocaleString` 不接受选项）。修复：补 `FixedAsset` interface、`formatMoney` 入口 `Number()` 强转。
- **死代码** → 维护负担与潜在风险。`xlsx@0.18.5`（有 CVE-2023-30533 / CVE-2024-22363，项目实际只用 exceljs）、`api/transfers.ts` 的 `returnAsset`、`components/ImportDialog.vue`（无引用且字段错配）、`Dashboard.buildScopeParams`（后端忽略）。
- **文档漂移** → 误导开发。`CLAUDE.md`：Python 3.11（实际 3.13.9）、角色 5 级（实际 6 级含 `director`）、流转"6 种含 repair/scrap"（实际 purchase/assign/return/transfer/recovery）；Token 过期 models(30)/settings(7)/CLAUDE.md(30) 三处不一致。
- **项目卫生**：根目录误建的 `-p/` 空目录删除；`docs/USER_MANUAL.md`（90KB）未跟踪，决定提交或忽略。

## Capabilities

### New Capabilities

- `write-authorization-scoping`: 读写操作的资源访问必须遵循权限声明与数据范围授权——敏感写（审批 / 入库 / 导入）必须声明权限码、业务发起的目标分公司 / 资产必须在用户授权范围内、用户列表与详情按范围隔离。
- `account-lifecycle-security`: 账号全生命周期安全——用户更新路径不得绕过 `set_password`（防账号接管）；停用账号必须联动失效其 Token；收尾 `remediate-audit-findings` 4.1 未落地的 create 默认弱口令移除。
- `inventory-state-machine-concurrency`: 盘点 `approve` 及所有状态机转换必须 `select_for_update` 锁任务行 + 二次状态校验，消除并发双扣（聚焦状态机层，与库存行锁互补）。
- `audit-log-completeness`: 审计装饰器必须兼容函数视图与 ViewSet 两种调用形态，改密等关键敏感操作不得静默漏审。
- `notification-data-scoping`: 通知收件人必须按数据范围授权收敛，不向无权查看该业务数据的用户推送含明细的通知。
- `frontend-contract-alignment`: 前端 API 字段名、URL 前缀、路由定义必须与后端序列化器契约严格对齐，并清理无引用的死代码。
- `frontend-type-and-performance`: 前端核心模型强类型化、金额格式容错、超大依赖懒加载以缩减首屏体积。

### Modified Capabilities

（无。`password-security` 与 `inventory-concurrency-control` 由 `remediate-audit-findings` 引入，但该提案尚未归档、未进入 `openspec/specs/`，无法对其做 delta；本提案以独立 New capability（`account-lifecycle-security`、`inventory-state-machine-concurrency`）延续其主题，待两提案一并归档时合并为同一 capability。）

## Impact

- **后端代码**：`apps/users/{serializers,views}.py`、`apps/permissions/permissions.py`（或新增统一写校验 helper）、`apps/transfers/views.py`、`apps/inventories/views.py`、`apps/assets/views.py`、`apps/authentication/{views,backends}.py`、`apps/audit/decorators.py`、`apps/notifications/signals.py`、`apps/transfers/{filters,models}.py`、`apps/inventories/serializers.py`。
- **前端代码**：`store/inventory.ts`、`views/{inventory/InventoryReport,AssetList,MobileScan}.vue`、`components/NotificationCenter.vue`、`api/{assets,transfers,categories}.ts`、`utils/format.ts`、`types/index.ts`、`vite.config.ts`（chunk 拆分）、`package.json`（删 xlsx）。
- **文档**：`CLAUDE.md`（Python 版本、角色级数、流转类型、Token 过期）。
- **测试**：新增写越权（跨 scope 建 transfer/inventory、check IDOR）、用户列表范围、并发双扣、改密审计、前端字段契约的回归测试。
- **运行时风险**：① 写操作补 scope 校验后，部分角色可操作的目标范围会收窄（预期）；② 用户列表收口后，依赖全量用户下拉的页面需确认改用范围接口；③ 删除默认弱口令后，存量 `123456` 账号需运维侧重置。
- **与 `remediate-audit-findings` 的关系**：本提案不重复其已落地的报表作用域 / 导入校验 / 限流 / transfer approve 并发；仅以 Modified 形式补齐 `password-security` 与 `inventory-concurrency-control` 的未尽事项，建议两提案一并实施后统一归档。
