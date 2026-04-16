## ADDED Requirements

### Requirement: Category 资产计数自动维护
系统 SHALL 通过 Django signal 在资产创建、更新、删除时自动更新关联分类的 `asset_count` 和 `in_stock_count` 字段。

#### Scenario: 新增资产时更新计数
- **WHEN** 通过采购入库创建新资产，关联到某个分类
- **THEN** 该分类的 `asset_count` SHALL 增加 1，如果资产状态为"在库"则 `in_stock_count` 同时增加 1

#### Scenario: 资产状态变更时更新计数
- **WHEN** 资产状态从"在库"变为"使用中"
- **THEN** 该分类的 `in_stock_count` SHALL 减少 1，`asset_count` 保持不变

#### Scenario: 删除资产时更新计数
- **WHEN** 删除某资产
- **THEN** 该分类的 `asset_count` SHALL 减少 1，如该资产为在库状态则 `in_stock_count` 同时减少 1

#### Scenario: 批量导入后计数准确
- **WHEN** 通过 Excel 批量导入 100 条资产
- **THEN** 所有受影响的分类计数 SHALL 正确反映导入后的数量
