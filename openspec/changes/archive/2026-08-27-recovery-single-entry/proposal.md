## Why

实例档案页的行内回收是**即时生效通道**（`RecoveryDialog` 传 `immediate: true` → 后端直接生成「已通过」单据并联动台账，绕过审批流）。v2-revision-issues.md 议题 6 定案（v2-revision-draft.md 修订 5.1，已入设计书修宪记录）：回收的唯一入口是回收单（新建 → 待审批 → 审批通过生效），行内即时回收取消；数据修正需求走台账调整单。修订倾向**彻底下线** immediate 通道（不留 admin 特例）。本案为拆案计划第 4 案。

## What Changes

- **删行内回收按钮与弹窗**：实例档案页（FixedAssetList）删除「回收」行内按钮与 `RecoveryDialog` 组件（全站唯一使用方），同步删其测试文件。资产明细页本无回收按钮，不受影响。
- **后端 immediate 通道彻底下线**：`_create_action` 删除 immediate_recovery 分支；请求携带 `immediate` MUST 拒绝（400，文案引导走回收单审批流）——不静默降级为待审批（调用方意图即时生效，静默降级会造成"以为回收了其实没有"的错觉，比报错危险）。
- **回收语义不变**：回收 = 从"在用"收回（在用−N → 回收库+N，或直接处置），去向二选一、实例退役、盘点锁、台账联动全部经审批生效路径（既有行为）。前端 `recoverAsset` API 保留（回收单创建页在用），删除 `immediate` 参数类型。
- **主 specs 措辞同步**：5 个 capability 中「即时生效」相关条文/措辞随之下线（recovery-list 行内入口 requirement 废除、transfer-line-items 的 immediate 语义、document-ledger-sync / transfer-asset-sync / document-instance-binding 的「或即时生效」措辞）。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `recovery-list`: REMOVED「从资产明细与固定资产列表行内直接回收」（行内入口与即时通道废除）；ADDED「回收入口唯一化」（唯一入口=回收单审批流，immediate 参数拒绝并引导）。
- `transfer-line-items`: 「五类创建 payload」requirement 中 `immediate` 语义由"保持"改为"下线并拒绝"；`draft` 语义不变。
- `document-ledger-sync`: 台账联动矩阵触发条件「审批通过（或按既有规则即时生效）」收窄为「审批通过」。
- `transfer-asset-sync`: 回收联动触发条件「（审批通过，或行内直接回收即时生效）」收窄为「审批通过」。
- `document-instance-binding`: 生效时点措辞「审批通过/即时生效」收窄为「审批通过」（并发终检语义不变）。

## Impact

- **前端**：删 `views/FixedAssetList.vue` 回收按钮/弹窗挂载/相关状态与 `views/assets/RecoveryDialog.vue`、`tests/views/RecoveryDialog.test.ts`；`api/transfers.ts` `recoverAsset` 删 `immediate` 参数类型。
- **后端**：`apps/transfers/views.py` 删 immediate_recovery 分支 + 拒绝携带 immediate 的请求；`tests/test_recovery_stock_link.py` immediate 用例组改造（通道拒绝 + 语义改走 approve 路径，语义已有覆盖的合并）。
- **兼容**：**BREAKING**（接口行为）：`POST /api/transfers/recovery` 携带 `immediate` 由"即时生效"变 400。唯一调用方 RecoveryDialog 同步删除，无存量调用方；数据修正场景引导走台账调整单（既有能力）。
- **无迁移**：纯行为变更，存量「已通过」的即时回收单历史数据不受影响。
