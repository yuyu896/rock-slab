# inventory-item-basis Specification（修改）

## RENAMED Requirements

- FROM: `### Requirement: 盘点差异为记录模式`
- TO: `### Requirement: 盘点差异自动生成调整单`

## MODIFIED Requirements

### Requirement: 盘点差异自动生成调整单

盘点审核通过时系统 MUST 在状态机锁内事务中对每个差异项（result 为 surplus 或 missing 且实盘数量非空）经唯一写入口生成调整单：目标列=在库数量（盘点只盘在库列）、变动量=实盘−应盘（盘盈为正、盘亏为负）、经办人=审批人、来源 MUST 关联盘点任务、事由 MUST 含任务名与前后数量。台账在库数量 MUST 随审批同步修正。任一差异调整将致负数时整笔审批 MUST 失败回滚（任务留在 pending_review，台账与调整单零变化，错误信息定位到分公司×品目）。漏盘归零规则（zero）产生的 missing 项 MUST 同样生成调整单；keep 规则下未盘项（unchecked）MUST NOT 生成。无差异项时 MUST NOT 生成任何调整单。

#### Scenario: 审核通过盘亏开单修账

- **WHEN** 盘点任务含差异项（应盘 5、实盘 3，台账在库 5）并审核通过
- **THEN** 生成一条调整单（在库 −2，经办人=审批人，来源=该任务），台账在库变 3

#### Scenario: 盘盈开正量调整单

- **WHEN** 差异项应盘 4、实盘 6，审核通过
- **THEN** 生成调整单（在库 +2），台账在库 4→6

#### Scenario: 调整致负数整笔回滚

- **WHEN** 差异项应盘 5、实盘 0，但审批时台账在库已被流转单扣至 1，审核通过
- **THEN** 审批失败返回 400（定位到该分公司×品目），任务留在 pending_review，台账无变化、不残留调整单

#### Scenario: 漏盘归零生成盘亏单

- **WHEN** 任务漏盘规则=zero，某项应盘 5 未盘，提交后该项记实盘 0/missing，审核通过
- **THEN** 该项生成调整单（在库 −5）；规则=keep 的任务中未盘项（unchecked）不生成

#### Scenario: 无差异不开单

- **WHEN** 盘点任务全部项 matched，审核通过
- **THEN** 不生成任何调整单，审批正常完成
