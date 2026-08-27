## Context

修订 5.1（设计书 2026-08-27 修宪记录）：回收唯一入口 = 回收单审批流。现状：

- 前端唯一即时回收入口：`FixedAssetList.vue:291`（仅"在用"实例显示，`canManageAssets` 门控）→ `RecoveryDialog.vue`（:71 `immediate: true`）→ `api/transfers.ts:55 recoverAsset({..., immediate})`。弹窗提示文案自陈"确认后立即生效"。`RecoveryDialog` 无其他使用方（仅 FixedAssetList + 其测试）。
- 后端：`transfers/views.py` `_create_action` 内 immediate_recovery 分支（校验 `manage_assets` → 单据直接落「已通过」+ 审批人/时间 → 创建后立即 `_apply_ledger`）。
- 回收单创建页 `RecoveryCreate.vue` 也调 `recoverAsset` 但不带 immediate（正常审批流，第 1 案已加在用预检）——保留不动。
- 台账/实例语义（去向二选一、回收=在用−N、实例退役不物理删除、盘点锁）在审批生效路径全部已有实现与测试覆盖。
- 主 specs 中 5 处「即时生效」条文/措辞（见 proposal Capabilities）。

## Goals / Non-Goals

**Goals:**
- 回收入口唯一：回收单（待审批 → 审批生效）；前端行内入口删除，后端 immediate 通道彻底下线（明拒）。
- 回收台账/实例语义零变化（全部仍在，只是触发时点只剩审批通过）。
- 主 specs 与行为同步（即时生效措辞清零）。

**Non-Goals:**
- 不做实例档案行 → 回收创建页的深链预填（修订要求"取消入口"，克制不加）。
- 不动 admin 数据修正路径——修订已定数据修正走台账调整单（既有能力）。
- 不动回收单创建页/审批端（第 1 案已修预检与文案）。
- 不清理历史「已通过」即时回收单数据（单据留痕是对账事实源）。

## Decisions

### D1：immediate 明拒（400），不静默降级
删除 immediate_recovery 分支后，`_create_action` 开头对 `request.data.get('immediate')` 为真即返回 400：「行内即时回收已下线：请创建回收单走审批流（数据修正走台账调整单）」。理由：传 immediate 的调用方意图是即时生效，静默按普通单建待审批会造成"以为已回收、实际挂起"的账实错觉，比报错危险；明拒 + 引导是唯一安全方向。备选（忽略参数照常建单）被弃。

### D2：前端物理删除入口，不留占位
删 FixedAssetList 的按钮、弹窗挂载、`openRecovery`/`showRecoveryDialog`/`recoveringAsset` 状态与 RecoveryDialog import；删 `RecoveryDialog.vue` 与 `RecoveryDialog.test.ts` 文件；`recoverAsset` 删 `immediate` 参数类型（函数保留——RecoveryCreate 在用）。不做行内"去回收"跳转占位——修订语义是入口取消而非改道；侧边栏"回收"菜单即新路径。

### D3：测试改造映射（test_recovery_stock_link.py）
| 现用例 | 处置 |
|---|---|
| test_immediate_applies_recycle_bin / test_immediate_dispose | 语义（去向二选一）approve 路径已有覆盖 → 删，换一条「immediate 请求 400 + 引导文案」 |
| test_immediate_fa_recovery_retires_instance | 实例退役语义 approve 路径已有（TestRecoveryFlow 前段 `_approve` 用例）→ 删 |
| test_immediate_without_manage_assets_rejected | immediate 特有语义消失 → 删（通道已不存在，无权限面可测） |
| test_immediate_blocked_by_inventory_lock | 创建路径盘点锁仍生效（`_check_inventory_lock` 通用段）→ 改写为普通回收单创建遇锁 400 |
| test_plain_recovery_without_immediate_stays_pending | 保留（普通创建照常待审批，回归锚点） |
新增：immediate=true（普通用户与持 manage_assets 用户两种）均 400 且不落库。

### D4：specs 同步以措辞收窄为主，recovery-list 为 REMOVED+ADDED
- recovery-list：旧 requirement 名为「从资产明细与固定资产列表行内直接回收」，与反转后内容矛盾 → REMOVED（Reason/Migration 注明）+ ADDED「回收入口唯一化」。
- 其余 4 个 capability：触发条件措辞收窄（"或即时生效"字样删除），requirement 名与主体语义不变 → MODIFIED 整块复制后微调；document-instance-binding 的并发 scenario 措辞"两张领用单（immediate 生效）"改为"两张领用单（先后审批通过）"——领用本无 immediate 通道，属历史措辞遗留，顺手纠正。

## Risks / Trade-offs

- [**BREAKING**：存量脚本/缓存的旧前端 bundle 传 immediate 会得到 400] → 报错文案直接引导新路径；前端唯一调用方同 PR 删除，窗口期不存在；生产 nginx 对 index.html 不缓存（既有部署配置），bundle 即时切换。
- [有人靠行内即时回收做数据修正] → 修订已定案该场景走台账调整单（事由留痕更合规）；400 文案中明示。
- [实例档案页"在用"实例失去快捷回收路径，操作步数变多] → 修订定案的治理成本（回收必须过审批）；审批端有差异预览与在用校验兜底。

## Migration Plan

纯行为变更，无迁移；部署即生效，回滚 = revert。历史即时回收单（「已通过」）是对账事实源，保留不动。

## Open Questions

（无——修订 5.1 已定"倾向彻底下线"，D1/D2 按此执行。）
