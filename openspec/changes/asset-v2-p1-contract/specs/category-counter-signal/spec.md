## REMOVED Requirements

### Requirement: Category 资产计数自动维护
**Reason**: 只盯 Asset 表的反范式计数违反铁律 1「每样信息只存一处」——Asset 冻结后计数随之失真失去意义；计数职责移交台账派生列与报表聚合。
**Migration**: 品目维度的数量统计由台账/报表按 (品目 × 分公司) 实时聚合提供，`asset_count`/`in_stock_count` 字段与计数信号下线。
