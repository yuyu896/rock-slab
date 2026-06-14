## Why

当前三种流转类型（采购入库、领用出库、调拨）共用同一套14列通用模板，不符合产品说明书中每种类型各自指定的列定义。此外，采购入库审批通过后没有"入库"操作步骤，库存不会实际变动——审批和入库被混为一步，无法区分"已审批待入库"和"已入库"状态。

## What Changes

- **采购入库模板**：按产品说明书重新定义为14列：采购日期、分公司、资产编号、物品名称、规格型号、图片、供应商、采购数量、单价、总金额、需求部门、采购经办人、备注
- **领用出库模板**：按产品说明书重新定义为10列：分公司、日期、领用物品、领用数量、用途、领用部门、部门累计领用、当前库存、是否核对、备注
- **调拨模板**：按产品说明书重新定义为14列：调拨日期、调出分公司、调出部门、调入分公司、调入部门、资产编号、资产名称、规格型号、调拨数量、调拨原因、调出负责人、调入负责人、备注
- **采购入库新增"入库"操作**：审批通过后新增 `warehoused`（已入库）状态，需手动点击"入库"按钮才将采购物品写入资产库存

## Capabilities

### New Capabilities
- `purchase-warehousing`: 采购入库流程新增"入库"操作步骤，审批通过后需手动确认入库，入库时更新资产库存
- `transfer-type-templates`: 三种流转类型各自独立模板定义，前端模板生成和后端导入导出均按类型区分

### Modified Capabilities

## Impact

- 前端文件：`frontend/src/utils/importTemplate.ts`（模板列定义）、`frontend/src/composables/useTransferList.ts`（模板下载/导入逻辑）、三个流转页面视图
- 后端文件：`backend/apps/transfers/views.py`（新增入库端点、导入导出按类型区分）、`backend/apps/transfers/models.py`（新增 warehoused 状态）
- API 变更：新增 `POST /api/transfers/{id}/warehouse` 入库操作端点
- 数据库变更：Transfer 模型 `审批状态` 新增 `已入库` 选项
