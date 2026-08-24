# report-data-scoping 增量

## ADDED Requirements

### Requirement: 报表数量口径按明细行聚合
流转类报表（调拨流水、领用统计、资产价值变动等）的数量与金额聚合 MUST 以明细行（`TransferLine`）为口径联查聚合，MUST NOT 引用单头已删除的平铺数量列；数据范围过滤规则（`resolve_user_scope`）与既有契约保持不变。

#### Scenario: 领用数量统计跨多行单据
- **WHEN** 某季度报表统计领用数量，期间存在一张含 品目 X×2、品目 Y×3 的领用单
- **THEN** 报表中品目 X 计 2、品目 Y 计 3，总领用计 5

#### Scenario: 数据范围过滤不因口径切换放松
- **WHEN** 无管理授权的用户请求调拨流水报表
- **THEN** 结果集仍为空（resolve_user_scope 过滤在明细行口径下同样生效）
