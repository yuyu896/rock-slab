## ADDED Requirements

### Requirement: 盘点 approve 在并发下只能生效一次

盘点任务审批通过（`approve`）MUST 在 `transaction.atomic()` 内对任务行执行 `select_for_update` 并进行二次状态校验；同一任务的两个并发 approve MUST 只有一个成功调整库存，另一个 MUST 返回 400/409 且不重复应用库存差异。

#### Scenario: 并发审批不导致库存双扣
- **GIVEN** 一个 expected=10、actual=8（diff=-2）的待审批盘点任务
- **WHEN** 两个用户近乎同时调用 `approve`
- **THEN** 最终资产数量只减少 2（10→8），不出现 8→6 的双扣

### Requirement: 所有盘点状态机转换必须原子化且加锁

盘点任务的每个状态转换（`start` / `submit` / `reject` / `cancel` / `recount` / `approve`）MUST 在事务内 `select_for_update` 锁定任务行后、重取并校验 `can_transition` 再写入；不得出现"无锁读状态 → 改字段 → save"的检查-执行窗口。

#### Scenario: 同一分公司并发开始盘点只允许一个
- **WHEN** 两个用户近乎同时对同一分公司调用 `start`（该分公司无活动盘点）
- **THEN** 只有一个 start 成功，另一个返回 400（已有进行中盘点）或 409，最终只有一个 in_progress 任务

#### Scenario: cancel 与 approve 并发结果可预测
- **WHEN** 一个 `cancel` 与一个 `approve` 近乎同时作用于同一任务
- **THEN** 任务最终处于且仅处于二者其一对应的终态，资产库存最多被调整一次
