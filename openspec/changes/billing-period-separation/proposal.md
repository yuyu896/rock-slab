# 租赁对账支持账期偏移

## 问题

当前租赁对账模块的 `ReconciliationTask.period` 字段同时承载两个语义：
1. **对账任务月份**：哪个月份导入/处理的任务
2. **结算账期**：该批订单实际结算的是哪个月的使用费用

这导致以下问题：
- 供应商 A：11月结算10月使用费（滞后1月）
- 供应商 B：11月结算11月使用费（同步）
- 供应商 C：11月结算12月使用费（提前1月）

当前设计无法区分这三种情况，金额计算会出现错误。

## 现状

- Excel 订单模板已有"记账日期"列（每行标注该设备从哪个月开始计费）
- `billing_for_period(period, accounting_date, monthly_rent)` 当前假设 `period` 就是结算账期
- 唯一约束 `(supplier, period)` 导致同一供应商在同月只能有一个任务

## 提案

新增 `ReconciliationTask.billing_period` 字段，从 Excel 的"记账日期"列提取结算账期：

1. **数据模型**：
   - `period`：对账任务月份（导入月份，用于列表筛选/归档分组）
   - `billing_period`：结算账期（从记账日期提取的年月，用于金额计算和业务逻辑）
   - 唯一约束改为 `(supplier, billing_period)`

2. **导入流程**：
   - 解析 Excel 时提取所有行的"记账日期"字段
   - 若一个文件包含多个月份 → 报错拒绝
   - 若该供应商的该结算账期已存在任务 → 报错提示

3. **金额计算修正**：
   - `billing_for_period(billing_period, accounting_date, ...)` 改为按结算账期计算

4. **前端展示**：
   - 列表页增加"结算账期"筛选器和列
   - 详情页 banner 同时显示"对账月份"和"结算账期"

## 影响范围

- 后端：models, services, views, serializers
- 前端：API 类型定义, 列表/详情/付款三个页面
- 数据迁移：存量任务从订单行回溯 `billing_period`

## 预期收益

- 支持不同供应商的不同账期规则
- 金额计算与财务结算口径一致
- 业务语义清晰（对账月份 vs 结算账期）
