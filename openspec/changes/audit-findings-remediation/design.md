## Context

磐盘已上线（qhpanpan.top），授权模型设计成熟（`OperationPermission` + `DataScopeMixin` + `resolve_user_scope` + 单会话 Token + 账号锁定），读路径的数据隔离经过 371 个后端测试验证基本可靠。但全面审查暴露一个**系统性短板**：**读路径有 `DataScopeMixin` 兜底，写路径既不统一声明权限、也不校验目标资源范围**——`OperationPermission` 对未声明 action 直接 `return True`，而流转 / 盘点 / 资产的写 action 多数未声明，`perform_create` / `_create_action` 也不调用 `resolve_user_scope`。叠加 `UserSerializer` 密码处理缺陷与盘点状态机无锁，构成可被直接利用的越权 / 提权 / 数据错账路径。

本设计聚焦"如何在最小改动面、不破坏既有产品语义的前提下，把写路径纳入与读路径同源的授权体系"，并修复前端与后端契约脱钩的功能 Bug。约束：① 不引入新外部依赖（账号锁定等已在 `remediate-audit-findings` 落地）；② 不做 schema 破坏性迁移；③ 保持既有测试全绿。

## Goals / Non-Goals

**Goals:**
- 写路径与读路径共用同一套权限 / 范围语义（`OperationPermission` 声明 + `resolve_user_scope` 校验），消除越权写。
- 堵住账号接管（密码 update 哈希）、盘点并发双扣、停用 Token 不失效三类数据 / 安全正确性 Bug。
- 前端字段 / URL / 路由与后端序列化器契约对齐，消除用户可感知的功能异常。
- 收敛手机号泄露面、通知跨范围推送面。

**Non-Goals:**
- 不改 `OperationPermission`「未声明即放行」的默认策略为白名单（风险过大，见 D3）。
- 不重写授权体系、不换 Token 方案（JWT / HttpOnly Cookie 等留待长期演进）。
- 不补前端测试覆盖率到后端水平（仅为本提案涉及的契约 Bug 加回归测试）。
- 不处理 `remediate-audit-findings` 已落地的报表作用域 / 导入校验 / 限流。

## Decisions

### D1. 密码 update 路径：password 不进 update 序列化器 + update 兜底 set_password
**选择**：`UserSerializer` 的 `password` 设为 **create-only**（update 时通过 `extra_kwargs` 或动态 `fields` 排除），密码变更一律走 `/api/auth/password/`（已有完整流程：校验旧密码 + `validate_password` + `set_password` + 轮换 Token）。同时在 `update` 里做防御性兜底：若 validated_data 仍含 password，`instance.set_password(validated_data.pop('password'))`。
**理由**：最小暴露面——写接口根本不应接受 password 字段。纯"update 重写 set_password"虽能堵漏洞，但留下了"经写接口改密可绕过旧密码校验"的语义漏洞（攻击者无需原密码即可改密），不可接受。
**备选**：单独 `UserUpdateSerializer` 不含 password——更干净但改动面大，create-only 已足够。

### D2. 写操作 scope 校验：抽统一 helper，复用 `resolve_user_scope`
**选择**：在 `core/permissions.py`（DataScopeMixin 同文件）新增 `validate_branches_in_scope(user, *branch_ids)` helper——对非 admin 用户，校验所有非空 branch_id 都在其 `resolve_user_scope(user).branches` 内，否则抛 `ValidationError`。`Transfer._create_action`、`InventoryTask.perform_create`、盘点 `check`（校验 `asset.branch == task.branch`）统一调用。
**理由**：与读路径 `get_scoped_queryset` 同源，避免每个 ViewSet 各写一份易漏；admin 自然豁免（其 scope 为全集）。
**备选**：在 serializer 的 `validate_branch` 里校验——可行但分散，且 transfer 的 branch 来自 `调出分公司` 文本回填，在 view 层统一更清晰。

### D3. `OperationPermission` 默认策略维持「未声明即放行」，但补全声明 + 加测试约束
**选择**：不改默认 `return True`，只为漏声明的写 action 补 `required_operations`（transfers 的 5 个业务 action + import_excel、assets 的 create）。新增一条**测试基线**：枚举所有 ViewSet 的写 action，断言其在 `required_operations` 有声明或显式标记 `public`，防回归。
**理由**：改白名单会令所有依赖"读放行"的接口瞬间 403，回归面与风险远大于收益；用"声明基线测试"在 CI 层卡住新增漏声明，成本最低。
**备选**：默认拒绝 + 显式 `public_actions` 白名单——更安全但需逐一标注所有读 action，工作量与风险不匹配。

### D4. 盘点状态机并发：抽 `_transition` helper，锁任务行 + 二次状态校验
**选择**：在 `InventoryTaskViewSet` 抽 `_transition(self, pk, target_status, **field_updates)`：`with transaction.atomic(): task = InventoryTask.objects.select_for_update().get(pk=pk); if not task.can_transition(target): raise 400; apply updates; task.save()`。`approve` 在锁内调 `_adjust_inventory`（其内部 asset 行锁不变），`start/submit/reject/cancel/recount` 全部改走该 helper。对齐 `TransferViewSet.approve`（已是正确范本）。
**理由**：并发双扣根因是"状态校验无锁 + asset 锁不能替代 task 锁"；锁 task 行后第二个并发请求重取即发现状态已变，二次校验拦截。helper 统一所有转换，杜绝 start 的"本分公司已有进行中盘点"检查窗口。
**备选**：仅给 approve 加锁——治标，其余转换仍有竞态（如双 cancel 与 approve 并发）。

### D5. 用户列表范围：list/retrieve 走 `_get_user_queryset`
**选择**：`UserViewSet.get_queryset` 移除 `list/retrieve` 的全量分支，统一返回 `_get_user_queryset(request.user)`。`set_system_avatar` 等基于 `get_object()` 的 action，在 queryset 中始终包含 `Q(id=request.user.id)`（`_get_user_queryset` 已保证本人可见），无需特例。
**理由**：与全项目数据隔离哲学一致；手机号即登录账号，属高敏 PII。
**备选（未采用）**：保留全量但 serializer 对非 admin 屏蔽 phone——治标，仍泄露组织结构与角色。**已决策采用本选择（直接按 scope 收口）**，不保留全员通讯录；若未来出现明确的跨范围选人硬需求，再以独立 capability 评估（见 Open Questions 1）。

### D6. 通知收件人范围：按 `resolve_user_scope` 反查
**选择**：`notifications/signals.py` 的 `get_approvers_for_branch` 改为——对 `instance.调出分公司`，查所有 `resolve_user_scope(u).branches` 含该分公司的 active 用户（且角色符合审批 / 抄送语义），而非按角色全量返回。补齐 `director` 角色（`remediate-audit-findings` 9.x 未落地）。
**理由**：通知体含资产明细，收件人必须对源数据有授权，否则即数据泄露。
**备选**：仅按 region 过滤——粒度粗，仍可能跨分公司。

### D7. 前端契约对齐：以后端为契约源
**选择**：字段 / 过滤器 / URL 问题一律在后端补齐 + 前端对齐——`InventoryItemSerializer` 补 `asset_code/asset_name`；`TransferFilterSet` 加 `资产编号` 过滤器；前端 `store/inventory.ts` 删除改用 `deleteInventoryTask` 封装、`MobileScan` 读 `branch`、`AssetList` 详情按资产过滤。
**理由**：序列化器是唯一契约源，前端不应靠拼字段名猜测；后端补字段比前端硬编码更可维护。
**备选**：纯前端绕过（如详情抽屉前端按资产编号本地过滤）——但后端无过滤器时仍要拉全量，性能与正确性都差。

### D8. 前端大 chunk：功能级动态 import + 删死代码依赖
**选择**：`exceljs` 改为在导入 / 导出页面内 `await import('exceljs')` 动态加载；`xlsx@0.18.5` 从 `package.json` 直接删除（全仓零引用，且有 CVE）。`element-plus` 视情况按需导入（已有 `unplugin-vue-components` 则维持）。
**理由**：exceljs/xlsx 仅导入导出场景用到，不该进首屏 bundle；删 xlsx 既减包又去 CVE。
**备选**：`manualChunks` 拆分——只是挪 chunk，不减少首屏体积。

### D9. 死代码统一删除
**选择**：确认无引用后删除——`api/transfers.ts` 的 `returnAsset`、`components/ImportDialog.vue`（无引用且字段错配）、`Dashboard.buildScopeParams`（后端忽略）、后端 `Transfer.ACTION_RETURN` 若确认无路由入口则一并清理。
**理由**：死代码是误导源与潜在漏洞面（如 ImportDialog 绕过 axios 拦截器）。
**风险**：`ACTION_RETURN` 若有历史数据引用——**已决策（见 Open Questions 4）**：仅删前端入口与 `returnAsset`，后端保留 `ACTION_CHOICES` 常量与 `_sync_asset` 分支兼容存量，待服务器确认无存量 return 单后再评估删常量。

## Risks / Trade-offs

- **[写 scope 收紧 → 依赖全量用户 / 全分公司下拉的页面可能失效]** → Mitigation：上线前 grep 所有 `getUsers()` / 分公司下拉调用点，确认改为范围接口；`remediate-audit-findings` 已有同类收口经验。
- **[删默认密码 → 存量 `123456` 账号无法登录新流程]** → Mitigation：提供一次性脚本把存量弱口令账号置为"需重置"，由管理员重发；或首登强制改密。
- **[状态机加锁 → 高并发盘点吞吐略降]** → Mitigation：行锁粒度仅限单 task，影响可忽略；盘点本就是低并发操作。
- **[未声明即放行策略不改 → 未来仍可能漏声明新 action]** → Mitigation：D3 的声明基线测试在 CI 卡住新增写 action 的漏声明。
- **[通知收件人收口 → 可能漏通知真实审批人]** → Mitigation：依赖 `ManagementScope` 授权正确性，上线前人工核对各角色授权配置；保留 admin 兜底接收。
- **[删除 ACTION_RETURN → 历史 return 类型流转单的展示 / 统计]** → Mitigation：先仅删前端 `returnAsset` 与后端 action 路由，保留 `ACTION_CHOICES` 常量与 `_sync_asset` 分支以兼容存量数据，统计口径单独评估。

## Migration Plan

1. **后端先行（P0 安全）**：D1 密码 / D2 写 scope helper / D3 权限声明补全 / D5 用户列表——一个 commit，附回归测试（写越权、账号接管、列表范围）。
2. **后端数据一致性（P1）**：D4 状态机 helper / 停用失效 Token / 审计装饰器兼容 / 通知范围 / assign TOCTOU——一个 commit，附并发测试。
3. **后端契约字段**：InventoryItemSerializer 补字段、TransferFilterSet 加过滤器、check IDOR——一个 commit。
4. **前端契约对齐 + 死代码 + 性能**：一个 commit（删除 URL、报告字段、详情过滤、MobileScan、formatMoney、FixedAsset 类型、大 chunk、删 xlsx/returnAsset/ImportDialog）。
5. **文档 + 卫生**：CLAUDE.md 修正、删 `-p/`、USER_MANUAL 跟踪决策——一个 commit。
6. **回滚**：各 commit 相互独立，任一可单独 `revert`；无 schema 迁移，无需数据回滚脚本（除存量弱口令重置，属运维操作不进代码回滚）。

## Open Questions

1. ~~**用户列表**：是否需全员通讯录？~~ **[已决策 2026-07-27]** 采用直接按 scope 收口：非 admin 仅见授权范围内 + 本人，不保留全员通讯录、不对非 admin 单独暴露姓名/角色。理由：与全项目数据隔离哲学一致，手机号即登录账号属高敏 PII。实施时仅需确认 Organization 页非 admin 选人范围变小不阻断核心流程（见 tasks 2.3 ②）。
2. ~~**默认密码策略**：随机密码还是 400？~~ **[已决策 2026-07-28]** 采用必填 + 强度校验：建号 `password` 必填，未传返回 400，create 内走 `AUTH_PASSWORD_VALIDATORS` 拒弱口令。理由：与现有 Organization.vue 表单流程一致（管理员本就在表单输密码），改动最小、安全最强，无需实现首登改密机制。
3. ~~**盘点 `check` 语义**~~ **[已决策 2026-07-28]** 采用「只校验同分公司」：asset 必须属于 `task.branch`（`asset.branch_id == task.branch_id`），保留 `get_or_create` 语义。理由：核心安全问题是跨范围 IDOR，校验 branch 已解决；保留 get_or_create 不破坏「扫码补盘本分公司任意资产」的现有语义，改动最小。
4. ~~**`ACTION_RETURN`**：是否有线上历史 return 单？~~ **[已决策 2026-07-28]** 代码层面已无活跃入口（前端 `returnAsset` 死代码、后端无 `@action` 路由）。采用保守清理：删前端入口与 `returnAsset`，后端**保留 `ACTION_CHOICES` 常量与 `_sync_asset` 分支**以兼容可能的存量 return 单；待服务器确认生产库无存量后再评估删常量。
5. ~~**`docs/USER_MANUAL.md`**~~ **[已决策 2026-07-28]** 提交进仓（面向用户的成品文档，与 `DEPLOYMENT.md` 同级），`git add docs/USER_MANUAL.md`。
