## Context

修订 3.1（设计书 2026-08-27 修宪记录）落在流转写路径的授权校验上。现状：

- `core/permissions.py:54` `validate_branches_in_scope(user, *branches)` 要求全部分公司在授权范围内；`transfers/views.py:132`（创建）与 `:321`（编辑已驳回）对五种单据类型统一双边调用。
- 列表可见性已是双向：`TransferViewSet` 声明 `scope_transfer_fields = ('from_branch', 'to_branch')`（views.py:54），DataScopeMixin 按 Q OR 放行任一命中——调入方**看得到**涉及本分公司的调拨单（修订"只读可见"的可见半边已存在）。
- 但写动作无范围收紧：`approve`（:213）/`submit`（:259）/`resubmit`（:271）走 `get_object`（调入方可命中）+ 操作码校验，调入方持审批码即可审批对方发起的调拨；`update`（:321）双边校验恰好把只含调入方范围的用户挡在编辑外（单边化后需保持等效拦截）。
- 前端：`TransferCreate.vue` 调出/调入下拉数据源 `getBranches()` 本就全量（BranchViewSet 无 DataScope），创建被拒纯因后端校验；`TransferList.vue:96` 待审批一律显示 通过/驳回；`TransferDetail.vue` 详情页有审批入口；移动端 `ApprovalList.vue:160` 通过/驳回按操作码显隐（无范围判断）。
- `usePermission`/user store 只有操作码与角色，无授权范围分公司列表——前端判断"可否操作"缺数据源。

## Goals / Non-Goals

**Goals:**
- 调拨单创建/编辑仅要求调出分公司在授权范围内；调入分公司不设授权门槛。
- 调入方对调拨单严格只读：后端硬边界（写动作校验调出方范围）+ 前端无入口（canOperate 显隐）。
- 其余四种单据类型与既有授权行为零变化。

**Non-Goals:**
- 不做 PC 端审批按钮按操作码显隐（审计 P1 遗留，另案）；本案 canOperate 只解决"调入方只读"。
- 不改列表可见性口径（scope_transfer_fields 双向已满足修订）。
- 不动通知、审批流状态机、台账联动。
- 不处理调拨之外类型对"对方分公司"可见性的语义（purchase/assign 等无对方概念或维持现状）。

## Decisions

### D1：创建/编辑按 action_type 传参，不做通用开关
`_create_action` 内改为：

```python
if action_type == Transfer.ACTION_TRANSFER:
    validate_branches_in_scope(request.user, from_branch)      # 单边：只校验调出方
else:
    validate_branches_in_scope(request.user, from_branch, to_branch)  # 现状
```

`update` 同构（编辑后单据的分公司）。不做"给 validate_branches_in_scope 加 mode 参数"——调用处分支更直白，校验函数保持纯语义。备选（前端放开调入下拉 + 后端维持双边但调入白名单）被弃：修订明确是授权规则变化，不是白名单补丁。

### D2：调入方只读 = 写动作统一走调出方校验 helper
新增 `_assert_transfer_operable(user, transfer)`：仅当 `action_type == transfer` 且用户 scope 非 all 时，`validate_branches_in_scope(user, transfer.from_branch)`（不通过即 400「调入方分公司对此调拨单只读」）。挂载点：`approve`、`submit`、`resubmit`；`update` 由 D1 的编辑校验天然覆盖（只含调入方范围者过不了"调出方在范围内"）；`warehouse`/`import_excel` 与调拨无交集不动。核心理由：审批即写台账两边（扣A加B），权限锚定在发起方（调出方），与创建校验同锚点、规则单一。移动端与 PC 全部经同一批端点，后端收一口即全覆盖。

### D3：canOperate 由后端序列化器输出，scope 经 context 每请求解析一次
`TransferSerializer` 增只读 `canOperate`：transfer 类型 = `scope.all or transfer.from_branch_id in scope.branches`，其余类型恒 `true`。`resolve_user_scope` 在 viewset 的 `get_serializer_context` 里解析一次挂 context（list 50 行不再逐行查库），serializer 只读 context。前端零新增请求。备选（前端拉用户范围自行比较）被弃：user store 无范围数据，为显隐按钮新增范围接口成本高于一个序列化字段。

### D4：前端三处显隐，语义"仅隐藏不可操作的调拨入口"
- `TransferList.vue` 操作列：写按钮（通过/驳回）外包 `v-if="item.canOperate !== false"`（宽容旧字段缺失）；详情按钮不隐藏（只读可见允许看详情）。
- `TransferDetail.vue`：审批操作条按 `canOperate` 显隐。
- `mobile/ApprovalList.vue`：通过/驳回按钮在既有 canApprove（操作码）判断上叠加 canOperate。
不做"只读徽标/提示文案"类装饰（Excel 朴素原则）；后端 400 文案「调入方分公司对此调拨单只读」兜底直连 API 的场景。

## Risks / Trade-offs

- [调入方持审批码者失去对调入调拨的审批权，可能改变既有审批习惯] → 修订明文"不可操作"；单据仍出现在其列表可见业务进展；需要时由调出方或更高级别（范围含调出方）审批。
- [canOperate 依赖 serializer context，离线调用（如 signal/celery 序列化）无 request] → 无 context 时默认 true（与现状一致），仅 API 响应路径输出真实值。
- [创建校验放开后，错选调入分公司的单据会进入对方列表] → 对方只读可见恰是修订要的透明性；台账完整性由单据留痕 + `check_ledger_consistency` 对账兜底（修订原文依据）。
- [编辑路径 D1 单边化后，调入方编辑调入调拨单被"调出方不在范围"拦下，报错文案沿用通用「您只能操作授权范围内的分公司」] → 语义正确；不为此做分型文案。

## Migration Plan

纯行为变更（无迁移/数据），部署即生效；回滚 = revert。存量单据无影响（校验仅作用于新请求）。

## Open Questions

（无——修订 3.1 已定案，D2 挂载点集合为修订"不可操作"的完整写面。）
