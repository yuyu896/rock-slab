# asset-batch-import 增量

## ADDED Requirements

### Requirement: 采购导入分公司行级守卫

采购批量导入 MUST 对「分公司」列做行级校验：列为空/空白计入行级错误跳过（提示分公司为空），MUST NOT 建出无分公司的采购单。守卫与既有编号/字典行级校验同形态（错误收集不中断整表）。

#### Scenario: 分公司空行被拒

- **WHEN** 导入文件某行分公司列为空（其余行正常）
- **THEN** 该行计入 errors（含分公司为空提示）跳过，不建单；其余行正常导入
