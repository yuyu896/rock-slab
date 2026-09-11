# fixed-asset-instance 增量

## MODIFIED Requirements

### Requirement: 内部编号锁行发号

内部编号 MUST 经实例序列计数行（`InstanceSequence`，**品目 × 分公司**一行）以 `select_for_update` 锁行自增生成，格式 `{品目编号}-{分公司代码}-{分公司内序号}`（如 `A-a00007-JH002-1`）；每分公司每品目各自从 1 起号；MUST NOT 使用 count() 等存在并发竞态的方案；唯一约束兜底，并发生成 MUST NOT 重号。同分公司同品目连续新增不重号；跨分公司各自独立起号（同序号不同代码不冲突）。分公司代码取分公司档案 `code` 字段。

#### Scenario: 连续新增不重号

- **WHEN** 品目 X 在金华二分已有实例至 X-JH002-6，金华采购单再生成 3 个实例
- **THEN** 新实例为 X-JH002-7、X-JH002-8、X-JH002-9，无重号

#### Scenario: 跨分公司独立起号

- **WHEN** 品目 X 在 A 公司已有 X-A001-9，B 公司首次采购品目 X 2 台
- **THEN** B 公司实例为 X-B001-1、X-B001-2

#### Scenario: 存量重编号

- **WHEN** 重编号命令在存量（金华品目 X 的 75 台，旧全局编号 X-792 等）上执行 --confirm
- **THEN** 全部改为 X-JH002-N（N 按原编号顺序从 1 连续重排），单据关联/序列号/图片随实例保留，重跑输出无需重编号
