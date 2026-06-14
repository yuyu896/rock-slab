## Context

当前流转系统三种类型（采购入库、领用出库、调拨）共用同一套14列通用模板（`TRANSFER_HEADERS`），不符合产品说明书中各自指定的列定义。模板在前端 `importTemplate.ts` 通过 xlsx 库生成，后端 `transfers/views.py` 也有对应模板/导入/导出端点使用 openpyxl。

采购入库流程缺少"入库"步骤：审批通过（`已通过`）后直接结束，Asset 模型不会被更新，库存不会变动。需要新增 `已入库` 状态和手动入库操作。

Transfer 模型现有字段（调拨日期、调出/调入分公司/部门、资产编号/名称、规格型号、数量、原因、负责人等）已涵盖采购和领用所需的大部分字段，但缺少部分字段如供应商、单价、总金额、需求部门、用途等。领用模板中的"部门累计领用"和"当前库存"为计算字段，需要查询得出。

## Goals / Non-Goals

**Goals:**
- 三种流转类型各有独立模板，列定义符合产品说明书
- 采购入库新增"入库"操作：审批通过 → 手动入库 → 更新资产库存
- 前后端模板、导入、导出保持一致

**Non-Goals:**
- 不修改资产导入模板（23列）和分类导入模板（7列）
- 不修改归还、维修、报废类型的模板（沿用通用模板）
- 不做实时库存推送

## Decisions

**1. 模板按类型拆分**
- `importTemplate.ts` 中新增 `PURCHASE_HEADERS`、`ASSIGN_HEADERS`、`TRANSFER_HEADERS`（重定义）三套独立列
- `generateTransferTemplate` 改为根据 type 参数选择对应 headers
- 后端 `download_template`、`export_excel`、`import_excel` 按 `action_type` 参数区分列映射

**2. Transfer 模型新增字段**
- 添加 `供应商`（CharField）、`单价`（DecimalField）、`总金额`（DecimalField）、`需求部门`（CharField）、`采购经办人`（CharField）、`用途`（CharField，领用用）
- 这些字段按类型使用，非对应类型时为空

**3. 新增"已入库"审批状态**
- `APPROVAL_CHOICES` 增加 `('已入库', '已入库')`
- 新增 `POST /api/transfers/{id}/warehouse` 端点
- 仅 `action_type=purchase` 且 `审批状态=已通过` 的记录可执行入库
- 入库操作：将 Transfer 中的资产信息写入 Asset 模型，设置入库日期，数量增加

**4. 领用模板中计算字段**
- "部门累计领用"和"当前库存"仅在导出时计算，不在导入模板中要求填写
- 导入模板使用简化版，导出时补充计算列

**5. 前端"入库"按钮**
- PurchaseList.vue 中，审批通过且未入库的记录显示"入库"按钮
- 调用 warehouse API 后刷新列表

## Risks / Trade-offs

- [数据库迁移] → 新增字段均为可选/有默认值，迁移安全无破坏性
- [现有数据兼容] → 新字段对旧记录为空，不影响已有数据 → 可接受
- [领用模板"是否核对"列] → 该字段在 Transfer 模型中无对应，导入时忽略，导出时固定为"待核对" → 后续可扩展
