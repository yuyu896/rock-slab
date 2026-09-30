## ADDED Requirements

### Requirement: 盘点启动原子一致与核对入口收敛

开始盘点（start）的清单生成 MUST 与状态转换在同一数据库事务内完成：生成失败（任何异常）时整体回滚，任务保持 pending 且不产生任何盘点项——「in_progress 且清单为空/不完整」的状态 MUST NOT 可达。盘点核对入口（check / check-instance）MUST 在事务内锁定任务行并复查状态后写核对结果（与状态机动作同锁串行）；台账盘核对 MUST 限定在开始盘点时生成的清单内，清单外的台账行 MUST 返回 404 且 MUST NOT 现场创建盘点项（与实例盘同口径）。实盘数量域为**非负整数**：API 提交负数 MUST 返回 400；Excel 导入的非整数（如 2.9）或不可解析值 MUST 进 errors 明确报错，MUST NOT 静默截断（整数数值格如 5.0 SHALL 正常接受）。

#### Scenario: 清单生成失败整体回滚

- **WHEN** start 的清单生成过程抛出异常
- **THEN** 任务状态保持 pending、盘点项零条，该分公司不被锁定（建单等操作不受影响）

#### Scenario: 清单外台账行核对被拒

- **WHEN** 对 in_progress 台账盘任务提交不在其清单内的台账行进行 check
- **THEN** 返回 404（提示清单于开始盘点时生成），不创建盘点项

#### Scenario: 负数实盘被拒

- **WHEN** check 提交 qty 为负数
- **THEN** 返回 400，盘点项不变

#### Scenario: 导入小数实盘报错

- **WHEN** 盘点结果 Excel 导入的某行实盘数量为 2.9
- **THEN** 该行进 errors（实盘数量必须为整数），不写入核对结果；数值 5.0 的整数行正常导入

#### Scenario: 核对与状态转换串行

- **WHEN** check 与 submit/approve 并发到达同一任务
- **THEN** 两者按任务行锁串行执行，已离开 in_progress 的任务核对返回 400
