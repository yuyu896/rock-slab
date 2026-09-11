# purchase-warehousing 增量

## ADDED Requirements

### Requirement: 采购入库列表分公司筛选

采购入库列表筛选区 SHALL 提供分公司筛选（口径=入库分公司/调入方）：可键入搜索（复用 BranchFilterSelect），空=不过滤，筛选参数 `toBranch` 与既有 filterset 对齐；关键字/状态筛选保持不变。

#### Scenario: 按入库分公司筛选

- **WHEN** 大范围账号在采购列表键入「杭州」选中某分公司
- **THEN** 列表仅显示该分公司入库的采购单；清空恢复全部
