## Context

- 资产更新：`api/assets.ts updateAsset` 用 `request.put`（全量）；`AssetSerializer` 的 `资产编号` 为必填、`序号` 已 `required=False`、分公司/分公司编号 `read_only`；`validate()` 仅在 `资产编号` 非空时校验分类登记。编辑抽屉 `AssetEditDrawer` 提交部分字段（资产编号只读未提交）→ PUT 全量校验因缺资产编号失败。
- 采购：`Purchase.vue` 的 `saveDraft` 与 `submitOrder` 都调用 `submitPurchaseItems`，按 order.items 逐条 `purchaseAsset`（创建「待审批」transfer，**每物品一条 transfer，无聚合订单**）。`Transfer.APPROVAL_CHOICES` = 待审批/已通过/已驳回/已入库，无草稿。
- 审批入库：`approve` → 置「已通过」并 `_sync_asset`（仅 assign/return/transfer 有 handler，采购无）；`warehouse`（入库确认）单独更新库存（`F('数量')+调拨数量` 或建资产）并置「已入库」。前端 `PurchaseList` 在「已通过」时显示「入库」按钮调 warehouse。

## Goals / Non-Goals

**Goals:**
- 资产编辑（含改状态）提交成功。
- 采购可保存为草稿、后续提交进入审批。
- 采购审批通过即增加库存（无需再点入库）。

**Non-Goals:**
- 不把采购重构为聚合订单（保持每物品一条 transfer）。
- 不删除 `warehouse` 动作（保留；采购 approve 已直达已入库，warehouse 对采购不再可达但无害）。
- 不回溯历史数据（已通过的旧采购库存不变）。

## Decisions

### 决策 1：资产编辑用 PATCH
- **做法**：`updateAsset` 由 `request.put` 改 `request.patch`。
- **理由**：部分更新不要求全字段；`validate()` 在资产编号为空时已跳过，PATCH 安全。
- **备选**：抽屉补齐所有必填字段——改动大且不必要，**否**。

### 决策 2：草稿 = 新审批状态「草稿」
- **做法**：`APPROVAL_CHOICES` 加 `('草稿','草稿')`；`_create_action` 据 payload 的 `draft` 标志设 `审批状态`（草稿 / 待审批）；新增 `submit` 动作把「草稿」转「待审批」。前端 `saveDraft` 传 `draft=true`；列表显示草稿并提供「提交」。
- **理由**：复用 transfer 模型与每物品一条 transfer 的既有结构；草稿不进审批统计/流。
- **备选**：localStorage 草稿——非服务端、跨设备丢失，**否**。

### 决策 3：采购审批折叠入库（公共库存方法）
- **做法**：抽出 `_apply_warehouse_stock(transfer)`（存在资产则 `数量+=调拨数量`、置在库；不存在则创建）；`approve` 对采购类型通过时调用之并置「已入库」。`warehouse` 复用同方法（保留）。
- **理由**：满足「通过即入库、库存增加」；消除采购必须再点入库的额外步骤；避免逻辑重复。
- **备选**：保留两步、仅前端提示——未满足用户「通过后库存变化」诉求，**否**。

## Risks / Trade-offs

- **[草稿 choices 迁移]** 加 choices 会生成一个 `AlterField` 迁移（无数据变更）→ **接受**，部署随 migrate 即可。
- **[warehouse 对采购不可达]** approve(采购) 直达已入库后，「入库」按钮(v-if 已通过)不再出现 → **缓解**：保留 warehouse 动作无副作用；如需可后续移除。
- **[草稿每物品一条 transfer]** 草稿/提交均按物品逐条 → **接受**，与既有提交结构一致。
- **[历史已通过采购]** 旧数据库存不变 → **接受**，仅影响新审批。

## Migration Plan

1. 后端：审批状态加「草稿」+ 迁移；`_create_action` 支持 draft；`submit` 动作；`_apply_warehouse_stock` + approve(采购) 联动。
2. 前端：updateAsset→PATCH；saveDraft 传 draft；草稿显示 + 提交草稿。
3. 部署：`migrate`（choices）+ 前端构建。

## Open Questions

（暂无。）

> 已定：approve(采购) 折叠入库后，**移除**独立的「入库」动作与按钮——后端 `warehouse` 动作、前端 `warehouseTransfer` API、`PurchaseList` 的「入库」按钮与 `handleWarehouse` 一并删除；**保留**「已入库」状态（approve 直达）与「已入库」统计。改动只限这些冗余处，不动其他。
