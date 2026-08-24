# notification-data-scoping 增量

## ADDED Requirements

### Requirement: 多明细单据通知摘要
流转单触发的通知 MUST 以明细摘要描述单据：首行品目名称 +（行数大于 1 时）"等 N 项"、数量为各行合计；收件人收敛规则（按数据范围授权）保持既有契约不变。

#### Scenario: 多行单据通知显示摘要
- **WHEN** 一张含 品目 X×2、品目 Y×3 的领用单进入待审批
- **THEN** 通知文本形如「品目 X 等 2 项（共 5 件）」，不逐行罗列全部明细
