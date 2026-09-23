## MODIFIED Requirements

### Requirement: 内部编号锁行发号

内部编号 MUST 经实例序列计数行（`InstanceSequence`，品目×分公司一行）以 `select_for_update` 锁行自增生成，格式 `{品目编号}-{分公司code}-{序号}`；MUST NOT 使用 count() 等存在并发竞争的方案，MUST NOT 以编号字符串比较推断下一号；唯一约束兜底，并发生成 MUST NOT 重号。调拨换号（transfer-instance-renumber）与采购出生发号 MUST 同源走此计数器。

#### Scenario: 连续新增不重号

- **WHEN** 分公司 B 品目 X 已有实例至 X-B-6，采购单再生成 3 个实例
- **THEN** 新实例为 X-B-7、X-B-8、X-B-9，无重号

#### Scenario: 调拨换号与出生发号同源

- **WHEN** 同品目同分公司的采购生效与调拨生效并发取号
- **THEN** 两路均经该品目×分公司计数行串行自增，编号不重复
