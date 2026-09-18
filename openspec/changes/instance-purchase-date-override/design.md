# 采购日期个体覆盖 — 技术设计

## Context

get_采购日期 现为 `birth_line.transfer.调拨日期`；规格/供应商已建立个体覆盖+白名单模式；编辑弹窗（双栏）已有四项提交链路。

## Decisions

### D1：DateField null 覆盖列 + 两级派生

`采购日期 DateField(null=True, blank=True)`（migration additive；日期没有"空串"态，用 null）。`get_采购日期 = obj.采购日期 or (birth_line.transfer.调拨日期 if birth_line else None)`。

### D2：batch-update 白名单加单值 采购日期（入库日期联动）

`purchase_date = request.data.get('采购日期')`，非 None 即生效：设值时同事务写 `inst.采购日期 = d; inst.入库日期 = d`（业务规则：入库日期=采购日期）；'' / null 清除时两列都回退（采购日期清空、入库日期=birth_line.transfer.调拨日期，无出生行置空）。前端编辑弹窗 el-date-picker（value-format YYYY-MM-DD），提交含日期字段（清空传 null）。批量菜单不加日期项（逐台编辑为主，端点能力已备）。

## Risks / Trade-offs

（无——同模式第三例，链路已被验证）

## Migration Plan

additive migration 随部署；无回填。

## Open Questions

（无）
