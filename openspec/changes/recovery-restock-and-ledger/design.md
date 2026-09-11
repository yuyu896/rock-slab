# 回收重塑 — 技术设计

## Context

现行回收去向：recycle_bin（在用→回收库，此后靠领用来源=回收库出库）/ dispose（在用→退役）。现场管理无回收库概念。回收库渗透面：台账第三列、实例四态、领用来源、盘点库别、回收去向。生产存量：回收库实例 41、台账回收库合计 60。

## Goals / Non-Goals

**Goals:**

- 回收去向=重新入库（在用→在库）/直接处置（不变）
- 回收库入口全下线（领用来源、盘点库别），存量归一
- 新增回收台账界面（处置物资明细流水，只读）

**Non-Goals:**

- 台账「回收库数量」列、实例「回收库」态物理保留（存量档案，不再产生新量）
- 回收单界面/审批流/回收分类/处置方式不变
- 对账逻辑不动（回收库列全 0 后自然兼容）

## Decisions

### D1：去向枚举改义，回收库分支改直通在库

`Transfer.回收去向` 的 recycle_bin 值改为 **restock（重新入库）**——枚举值重定义（存量 recycle_bin 单据的历史语义按「当时入过回收库」档案保留，不回写）。`ledger.apply_document` 的 recovery 分支：目标列回收库→**在库**（COLUMN_RECYCLE→COLUMN_STOCK）；`instances.py` 的回收迁移：→ 回收库改为 → 在库。`expected_state` 不变（回收前置=在用）。领用来源校验收口：携带 recycle_bin 即 400。

### D2：存量归一命令 normalize_recycle_bin

新管理命令（默认预览，--confirm 执行）：实例 当前状态=回收库 → 在库（经 instances 服务层——架构测试白名单同 normalize_instance_status 先例）；台账逐 branch×item：回收库列 N → 回收库 -N、在库 +N（经 ledger.apply_adjustment 两条留痕，事由「回收库退役归一」）。幂等：全零后重跑报无需归一。

### D3：回收台账=单据派生的只读端点

`GET /api/transfers/recovery-ledger`（TransferViewSet 新 action）：queryset = recovery×dispose×生效单据的明细行，`select_related('item','transfer')` + 实例关联 prefetch；输出行 = 明细行展开（实例品目按 TransferLineInstance 逐台一行）。筛选用既有 filterset 扩展（分公司/日期/品目关键字）。权限与回收单列表一致（读走既有 scope）。前端新页 `RecoveryLedger.vue` + 路由 + 侧边栏（回收组内两入口：回收单/回收台账）+ 导出（openpyxl 同回收单导出模式）。

### D4：盘点库别收口

盘点创建页库别下拉删「回收库」选项；serializers 校验 stock_bin=recycle → 400（存量历史任务不受影响——不回写）。

## Risks / Trade-offs

- [去向枚举改义的存量兼容] → 存量 recycle_bin 单据照旧展示「入回收库」（历史事实）；新单据只产生 restock/dispose
- [对账] → 回收库列归零后镜像两侧皆 0，check_ledger_consistency 零差异保持
- [领用来源退役的遗漏调用] → 前后端 grep 收口 + 测试覆盖 recycle_bin 拒绝

## Migration Plan

无模型迁移（枚举改义走代码 + 存量不回写）。部署顺序：代码上线 → 跑归一命令（预览→确认）→ 对账验证。回滚：代码回退即可，已归一数据无破坏（在库↔回收库语义对称）。

## Open Questions

（无）
