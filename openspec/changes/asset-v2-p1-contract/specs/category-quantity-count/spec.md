## REMOVED Requirements

### Requirement: Category 资产总数量统计使用 Sum
**Reason**: `asset_total_quantity` 反范式计数字段随计数字段整体下线（铁律 1）；总量事实唯一存放于台账。
**Migration**: 品目总量由台账派生列聚合输出。

### Requirement: Category 在库数量统计使用 Sum 加状态过滤
**Reason**: `in_stock_quantity` 反范式计数字段随计数字段整体下线；且「Asset.当前状态」口径与台账四列口径不一致。
**Migration**: 在库数量由台账在库列聚合输出。
