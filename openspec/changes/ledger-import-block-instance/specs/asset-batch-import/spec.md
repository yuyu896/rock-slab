# asset-batch-import 增量

## ADDED Requirements

### Requirement: 台账导入拒绝实例管理品目

台账增量导入 MUST 在行级拒绝**实例管理**品目：命中品目字典但管理方式为 instance 的行计入行级错误（提示改走采购入库单/流转单），MUST NOT 进入差异预览、MUST NOT 在 confirm 时生成调整单。数量管理与消耗品品目 MUST 维持既有导入行为。该守卫 MUST 同时约束预览与确认两阶段（错误行不产生差异即可天然覆盖）。

#### Scenario: 实例品目行被拒

- **WHEN** 导入文件含实例管理品目 A-a00008 的行（其余为数量管理品目）
- **THEN** 预览返回的 diffs 不含该行，errors 含「实例管理品目不可台账导入」类提示；confirm 后该行无调整单生成

#### Scenario: 数量/消耗品不受影响

- **WHEN** 同一文件含数量管理与消耗品品目行
- **THEN** 两类行照常进入差异预览与确认流程
