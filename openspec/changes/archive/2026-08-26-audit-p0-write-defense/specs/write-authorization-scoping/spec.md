## MODIFIED Requirements

### Requirement: 写操作必须校验目标分公司在授权范围

流转创建（`purchase/assign/return/transfer/recovery`）、盘点任务创建、台账调整单创建、台账增量导入（差异预览与确认两阶段）、流转 Excel 导入 MUST 校验其 `from_branch` / `to_branch` / `branch` / 导入行所属分公司均在 `resolve_user_scope(request.user).branches` 内；admin 豁免。单对象接口任一目标分公司越界时 MUST 返回 400 且不落库；批量导入中越权行 MUST 进 `errors`（提示分公司不在授权范围）、不进入差异预览、不可被确认入账或建单，合法行照常处理。台账增量导入的差异预览 MUST NOT 向无权用户返回范围外分公司的台账现值。

#### Scenario: manager 为授权范围外的分公司发起调拨被拒

- **WHEN** 管辖区域 A 的 manager 发起一笔 `from_branch` 属于区域 B 的调拨
- **THEN** 系统返回 400，不创建流转单，资产库存不变

#### Scenario: supervisor 为授权范围外的分公司建盘点任务被拒

- **WHEN** 区域 A 的 supervisor 为区域 B 的分公司创建盘点任务
- **THEN** 系统返回 400，不生成盘点项、不污染目标分公司盘点状态

#### Scenario: 范围受限用户对范围外分公司开调整单被拒

- **WHEN** 持 `adjust_ledger` 授权但数据范围仅含分公司 A 的用户，以分公司 B 为目标 POST 台账调整单（以 id 或名称指定分公司）
- **THEN** 系统返回 400，不生成调整单，B 台账数量不变

#### Scenario: 台账导入的越权行不泄露现值也不可入账

- **WHEN** 数据范围仅含分公司 A 的用户上传含 B 分公司行的台账增量文件
- **THEN** 预览响应的 `diffs` 不含 B 行且不返回 B 的现值，B 行进 `errors` 提示不在授权范围；`confirm=1` 时仅 A 行生成调整单

#### Scenario: 流转导入的越权行不建单

- **WHEN** 数据范围仅含分公司 A 的用户上传含「调出分公司=B」行的流转导入文件
- **THEN** 该行进 `errors` 提示不在授权范围，不创建 B 的待审批单据，合法行照常建单

## ADDED Requirements

### Requirement: 盘点任务分公司必填且不可经更新接口变更

盘点任务创建 MUST 携带 `branch`（必填）并通过授权范围校验；`branch` 与 `status` MUST 为只读字段——经更新接口（PATCH/PUT）提交的 `branch` / `status` MUST NOT 改变任务对应字段值，任务状态仅能经状态机动作（开始/提交/审批/驳回/重盘）流转。分公司为空 MUST NOT 触发全公司台账行的盘点项生成。

#### Scenario: 创建盘点任务缺分公司被拒

- **WHEN** 用户 POST 盘点任务且未携带 `branch`
- **THEN** 系统返回 400，不创建任务

#### Scenario: PATCH 改分公司或状态不生效

- **WHEN** 用户对 pending 盘点任务 PATCH `{"branch": "<范围外分公司>", "status": "completed"}`
- **THEN** 任务的 `branch` 与 `status` 均保持原值；任务不进入 completed，差异调整单不因该请求生成
