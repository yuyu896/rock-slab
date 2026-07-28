## 1. P0 — 写操作权限声明与目标范围校验（write-authorization-scoping）

- [x] 1.1 在 `core/permissions.py` 新增 `validate_branches_in_scope(user, *branch_ids)` helper：非 admin 校验所有非空 branch_id ∈ `resolve_user_scope(user).branches`，越界抛 `ValidationError`；admin 豁免。
- [x] 1.2 ~~`apps/transfers/views.py` 的 `required_operations` 补全 `purchase/assign/return_asset/transfer/recovery/import_excel` → `manage_assets`~~ **[实施时纠正]** 经 `test_rbac_matrix::test_purchase_staff_allowed` 核实：业务发起（purchase/assign/return/transfer/recovery）对所有登录用户开放是**产品设计**（员工申请领用/采购），非漏洞，不补 `manage_assets`；仅 `import_excel` 补声明 `manage_assets`。
- [x] 1.3 `TransferViewSet._create_action` 在 `Transfer.objects.create` 前调用 `validate_branches_in_scope(request.user, from_branch, to_branch)`；`perform_update` 同步校验改动后的分公司。
- [x] 1.4 `apps/inventories/views.py` 的 `perform_create` 调用 `validate_branches_in_scope(self.request.user, serializer.validated_data.get('branch'))`。
- [x] 1.5 ~~`apps/assets/views.py` 的 `required_operations` 补 `create` → `manage_assets`~~ **[实施时纠正]** 经 `test_rbac_matrix::test_create_asset_leader_allowed` 核实：资产 `create` 对所有登录用户开放（min_role staff 语义）是产品设计，不补 `manage_assets`（撤销）。
- [x] 1.6 盘点 `check` 接口的 asset 查询改为 `Asset.objects.filter(id=..., branch=task.branch).first()`，不存在返回 404；保留后续 `get_or_create` 语义（仅纳入本分公司资产，决策见 design Q3）。
- [x] 1.7 新增写权限声明基线测试（`test_write_scope.py::TestWritePermissionBaseline`）：断言 transfers 的 `import_excel/approve/warehouse`、assets 的 `update/partial_update/destroy/import_excel/batch_delete` 在 `required_operations` 中声明，防回归。
- [x] 1.8 新增写越权回归测试（`test_write_scope.py::TestWriteScopeEnforcement`）：跨 scope 建 transfer/inventory 被拒（400）、范围内通过（201）、check 跨范围 asset 被拒（404）。

## 2. P0 — 用户列表数据范围（write-authorization-scoping）

- [x] 2.1 `apps/users/views.py` 的 `get_queryset` 移除 list/retrieve/set_system_avatar 的全量分支，统一返回 `_get_user_queryset(request.user)`。
- [x] 2.2 确认 `_get_user_queryset` 恒包含 `Q(id=request.user.id)`，使基于 `get_object()` 的 avatar 等动作对本人仍可用。
- [x] 2.3 核实收口对前端的影响（已知调用点：`views/Organization.vue:468` `fetchUsers` 无参数拉全量、`views/admin/PermissionAssign.vue:229` `getUsers` 无参数）。逐项确认：① PermissionAssign 为 admin 专用页，admin 豁免→确认无影响即可；② Organization 页非 admin 选人范围将变小（已决策直接按 scope 收口，不保留全员通讯录）——确认无"必须跨范围选人"的硬需求阻断核心流程；③ 建号/编辑表单的"选择领导/审批人"下拉是否依赖看到范围外用户；④ 收口后非 admin 仍能完成其授权内的组织管理与选人操作。
- [x] 2.4 新增测试（`test_write_scope.py::TestUserDirectoryScoping`）：非 admin 用户 list 仅见范围内 + 本人、retrieve 范围外用户 404。

## 3. P0 — 账号生命周期安全（account-lifecycle-security）

- [x] 3.1 `apps/users/serializers.py`：`password` 设为 create-only（`update` 中 `pop` 掉，绝不走默认 setattr 原样写入）；`update` 重写为丢弃 password 字段（防账号接管）。
- [x] 3.2 `UserSerializer.create` 移除默认 `'123456'`；`password` 必填，未传或为空返回 400，并在 create 内调用 `password_validation.validate_password`（走 `AUTH_PASSWORD_VALIDATORS`，拒弱口令）。决策见 design Q2。
- [x] 3.3 前端配套（与 3.2 同批改）：`views/Organization.vue` 去掉建号表单的 `password: '123456'` 预填（line 441 改空），新增 password 输入框（仅新建显示），`payload.password` 去 `|| '123456'` fallback 并加 ≥8 位必填校验；编辑用户分支本就不提交 password（payload 无该字段），符合 3.1 create-only。
- [x] 3.4 停用账号：`UserSerializer.update` 中 `status=inactive` 同步 `is_active=False` 并删除其全部 `ExpiringToken`（启用则恢复 `is_active`）；`ExpiringTokenAuthentication` 额外校验 `status=='active'`。
- [x] 3.5 新增测试（`test_account_lifecycle.py`）：经 update 注入预生成哈希无法接管账号、建号未传/弱口令被拒、停用后旧 token 401。

## 4. P1 — 盘点状态机并发（inventory-state-machine-concurrency）

- [x] 4.1 `apps/inventories/views.py` 抽 `_transition(self, pk, target_status, **field_updates)`：`with transaction.atomic(): task = InventoryTask.objects.select_for_update().get(pk=pk); if not task.can_transition(target): return 400; apply; task.save()`。
- [x] 4.2 `approve` 改走 `_transition`，在锁内调用 `_adjust_inventory`（asset 行锁保持）。
- [x] 4.3 `start/submit/reject/cancel/recount` 全部改走 `_transition`；`start` 的"本分公司已有进行中盘点"检查移入锁内。
- [x] 4.4 新增并发测试：双 approve 不双扣（expected=10/actual=8 → 仅扣 2）、同分公司并发 start 仅一个成功、cancel 与 approve 并发结果确定。

## 5. P1 — 数据一致性与合规（audit-log-completeness / notification-data-scoping / TOCTOU）

- [x] 5.1 `apps/audit/decorators.py` 兼容 FBV：`args[0]` 为 `HttpRequest` 时直接作为 request，否则取 `getattr(args[0], 'request', None)`。
- [x] 5.2 `apps/notifications/signals.py` 的审批/抄送收件人改为按 `resolve_user_scope(recipient).branches` 含 `调出分公司` 过滤，补齐 `director` 角色。
- [x] 5.3 `apps/transfers/views.py` 的 `assign` 库存校验并入 `_sync_asset` 事务（`select_for_update` 后再判数量），消除 TOCTOU。
- [x] 5.4 新增测试：改密写审计、通知不跨范围、assign 并发不超发。

## 6. P1 — 前端契约对齐（frontend-contract-alignment）

- [x] 6.1 后端 `InventoryItemSerializer` 增补 `asset_code`（source `asset.资产编号`）、`asset_name`（source `asset.资产名称`）。
- [x] 6.2 后端 `TransferFilterSet` 增加 `资产编号` 过滤器（`django_filters.CharFilter`）。
- [x] 6.3 前端 `store/inventory.ts` 删除改用 `api/inventories.ts` 的 `deleteInventoryTask(id)`（带 `/api` 前缀）。
- [x] 6.4 前端 `InventoryReport.vue` 改渲染 `assetCode/assetName`。
- [x] 6.5 前端 `AssetList.viewDetail` 按当前资产过滤流转；`MobileScan.vue` 读 `branch` 而非 `branchId`。
- [x] 6.6 修复半成品入口（本批完成：通知中心"查看全部"改跳 `/mobile/notifications`、`NotificationCenter` `onUnmounted` 解绑 click 监听；**快捷筛选/批量调拨待后续**——需后端 lowStock 过滤与调拨带参路由，暂保留 UI 不误导）。
- [x] 6.7 清理死代码：删除 `components/ImportDialog.vue`、`api/transfers.ts` 的 `returnAsset`、`Dashboard.buildScopeParams`；`api/categories.ts` 的 `exportCategories` 改走 `request` 实例。后端 `ACTION_RETURN` 因无 `@action` 路由，**保留 `ACTION_CHOICES` 常量与 `_sync_asset` 分支**兼容可能存量，仅删前端入口（决策见 design Q4）；待服务器确认无存量 return 单后再评估删常量。
- [x] 6.8 新增前端契约测试：删除调用走封装、报告字段非空、详情按资产过滤。

## 7. P2 — 前端类型与性能（frontend-type-and-performance）

- [ ] 7.1 `types/index.ts` 补 `FixedAsset` interface（对照 `FixedAssetSerializer`），替换 `api/assets.ts` 与 `FixedAssetList.vue` 中的 `any`。
- [ ] 7.2 `utils/format.ts` 的 `formatMoney` 入口 `const v = Number(value) || 0` 强转并兜底 NaN。
- [ ] 7.3 `exceljs` 改为导入/导出页面内 `await import('exceljs')` 动态加载；从 `package.json` 删除 `xlsx@0.18.5`（确认零引用后）。
- [ ] 7.4 `npm run build` 验证首屏 chunk 不含 `exceljs`、产物无 `xlsx`。

## 8. 文档与项目卫生

- [ ] 8.1 修正 `CLAUDE.md`：Python 3.11 → 3.13.9；角色 5 级 → 6 级（补 `director`）；流转 6 种含 repair/scrap → 实际 5 种（purchase/assign/return/transfer/recovery）；Token 过期统一为 7 天（models fallback 同步）。
- [ ] 8.2 删除根目录误建的 `-p/` 空目录。
- [ ] 8.3 `docs/USER_MANUAL.md` 提交进仓（决策见 design Q5），`git add docs/USER_MANUAL.md`。

## 9. 全量验收

- [ ] 9.1 `pytest --tb=short` 全绿（本批 P0 后 383 passed；P1/P2 实施后重跑确认无回归）。
- [ ] 9.2 `npm run build` 与 `npm run test` 通过（本批 build 已通过）。
- [ ] 9.3 `openspec validate audit-findings-remediation` 通过；确认与 `remediate-audit-findings` 无 spec 冲突。
