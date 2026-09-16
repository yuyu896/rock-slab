# fixed-asset-instance 增量

## ADDED Requirements

### Requirement: 序列健康口径与改名后体检

各「分公司 × 品目」实例编号序列（InstanceSequence.last_no）SHALL 等于该分组**现存实例数**（编号从 1 连续无空洞）；last_no 大于现存实例数即为**发号基础污染**（历史数据清理/分公司改名错位残留），SHAL 经 `renumber_instances` 归位。分公司改名（或任何 Branch 字段变更）操作后，运维 MUST 执行 `check_ledger_consistency` 并抽查序列健康（last_no vs 实例数），错位未处置前不得放行后续批量导入审批。

#### Scenario: 序列污染识别

- **WHEN** 某分组序列 last_no=82 而现存实例 41 台
- **THEN** 判定发号基础污染，执行重编号后编号为 -1..-41、序列=41

#### Scenario: 重编号后正常续号

- **WHEN** 重编号完成（-1..-41，序列=41），新采购 1 台生效
- **THEN** 新实例编号 -42（连续无跳号）
