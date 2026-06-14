## ADDED Requirements

### Requirement: Category 资产总数量统计使用 Sum
Category 的资产总数量统计 SHALL 使用 `Sum('数量')` 聚合而非 `.count()` 行数。

#### Scenario: 单条 Asset 数量大于 1
- **WHEN** 一个 Category 下有一个 Asset 行，其 `数量` 字段为 10
- **THEN** 该 Category 的 `asset_total_quantity` 为 10，`asset_count` 为 1

#### Scenario: 多条 Asset 各有不同数量
- **WHEN** 一个 Category 下有 3 个 Asset 行，数量分别为 5、3、2
- **THEN** 该 Category 的 `asset_total_quantity` 为 10，`asset_count` 为 3

### Requirement: Category 在库数量统计使用 Sum 加状态过滤
Category 的在库数量统计 SHALL 使用 `Sum('数量')` 并过滤 `当前状态='在库'`。

#### Scenario: 部分资产在库
- **WHEN** 一个 Category 下有 2 个 Asset 行，一个在库（数量 5），一个使用中（数量 3）
- **THEN** 该 Category 的 `in_stock_quantity` 为 5，`in_stock_count` 为 1
