# write-authorization-scoping Specification

## Purpose
TBD - created by archiving change audit-findings-remediation. Update Purpose after archive.
## Requirements
### Requirement: 敏感写 action 必须声明权限码

审批、入库、导入、批量删除等敏感写 action MUST 在 ViewSet 的 `required_operations` 中显式声明所需操作码，未声明的此类写 action 不得放行。业务发起类 action（流转 `purchase/assign/return/transfer/recovery`、资产 `create`）按产品设计对所有登录用户开放（员工申请领用 / 采购 / 登记资产），不要求 `manage_assets`，其数据范围由「写操作必须校验目标分公司在授权范围」约束。

#### Scenario: 流转导入未授权被拒
- **WHEN** 一个无 `manage_assets` 授权的用户 `POST /api/transfers/import-excel`
- **THEN** 系统返回 403，不解析文件

#### Scenario: 业务发起对所有登录用户开放但受范围约束
- **WHEN** 一个已登录用户 `POST /api/transfers/transfer`（或 purchase / assign 等业务发起）或 `POST /api/assets/`
- **THEN** 接口不在权限层拒绝；若目标分公司超出其授权范围，由范围校验返回 400

### Requirement: 写操作必须校验目标分公司在授权范围

流转创建（`purchase/assign/return/transfer/recovery`）、盘点任务创建、台账调整单创建、台账增量导入（差异预览与确认两阶段）、流转 Excel 导入 MUST 校验其 `from_branch` / `to_branch` / `branch` / 导入行所属分公司均在 `resolve_user_scope(request.user).branches` 内；admin 豁免。**调拨（transfer 类型）为例外：创建与编辑仅校验调出分公司（from_branch）在授权范围内，调入分公司不要求授权**（修订 3.1：跨范围调拨由单边发起，台账完整性由单据留痕与对账兜底）。其余类型维持全部分公司校验。单对象接口任一应校验分公司越界时 MUST 返回 400 且不落库；批量导入中越权行 MUST 进 `errors`（提示分公司不在授权范围）、不进入差异预览、不可被确认入账或建单，合法行照常处理。台账增量导入的差异预览 MUST NOT 向无权用户返回范围外分公司的台账现值。

#### Scenario: manager 为授权范围外的分公司发起调拨被拒

- **WHEN** 管辖区域 A 的 manager 发起一笔 `from_branch` 属于区域 B 的调拨
- **THEN** 系统返回 400，不创建流转单，资产库存不变

#### Scenario: 调入分公司不在授权范围不阻断调拨

- **WHEN** 管辖区域 A 的 manager 发起一笔 `from_branch` 属于区域 A、`to_branch` 属于区域 B 的调拨
- **THEN** 单据创建成功进入待审批，区域 B 不要求任何授权

#### Scenario: 非调拨类型双边校验不回归

- **WHEN** 数据范围仅含分公司 A 的用户创建一笔 to_branch 为分公司 B 的非调拨类型单据（如归还）
- **THEN** 系统返回 400，不落库（调拨例外不外溢到其他类型）

#### Scenario: 流转导入的调拨行同口径单边

- **WHEN** 数据范围仅含分公司 A 的用户上传调拨导入文件，某行调出分公司=A、调入分公司=B
- **THEN** 该行照常建单进入待审批（调入越界不拒）；调出分公司=B 的行仍进 `errors` 不建单

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

### Requirement: 盘点 check 必须校验资产属于任务所属分公司

盘点 `check` 接口 MUST 限定提交的 `asset` 属于 `task.branch`；提交不属于该分公司的资产 MUST 返回 404，且不得创建盘点项。

#### Scenario: 提交跨范围资产进行盘点被拒
- **WHEN** 持 A 分公司盘点权限的用户对 A 分公司任务提交一个 B 分公司资产的 `asset_id`
- **THEN** 系统返回 404，不创建 InventoryItem，审批后该资产库存不受影响

### Requirement: 用户列表与详情必须遵循数据范围隔离

`UserViewSet` 的 list / retrieve MUST 返回 `_get_user_queryset(request.user)` 过滤后的结果（admin 全量；其余为授权组织节点内 + 本人）；不得向无权用户暴露范围外用户的 `phone`（登录账号）。

#### Scenario: 非 admin 用户只能看到范围内的用户
- **WHEN** 一个 manager 调用 `GET /api/users/`
- **THEN** 响应仅包含其授权范围内的用户与本人，不包含其他区域用户

#### Scenario: 无授权用户看不到全公司手机号
- **WHEN** 一个无 `manage_users` 授权的 staff 调用 `GET /api/users/`
- **THEN** 响应不包含其授权范围外任何用户的 `phone` 字段

### Requirement: 盘点任务分公司必填且不可经更新接口变更

盘点任务创建 MUST 携带 `branch`（必填）并通过授权范围校验；`branch` 与 `status` MUST 为只读字段——经更新接口（PATCH/PUT）提交的 `branch` / `status` MUST NOT 改变任务对应字段值，任务状态仅能经状态机动作（开始/提交/审批/驳回/重盘）流转。分公司为空 MUST NOT 触发全公司台账行的盘点项生成。

#### Scenario: 创建盘点任务缺分公司被拒
- **WHEN** 用户 POST 盘点任务且未携带 `branch`
- **THEN** 系统返回 400，不创建任务

#### Scenario: PATCH 改分公司或状态不生效
- **WHEN** 用户对 pending 盘点任务 PATCH `{"branch": "<范围外分公司>", "status": "completed"}`
- **THEN** 任务的 `branch` 与 `status` 均保持原值；任务不进入 completed，差异调整单不因该请求生成

### Requirement: 调拨单调入方只读

调拨单（transfer 类型）对调入方分公司为**只读**：涉及本分公司的调拨单 MUST 出现在调入方用户的列表（既有 `scope_transfer_fields` 双向可见口径不变）；其写操作——审批（通过/驳回）、草稿提交（submit）、驳回后重新提交（resubmit）、驳回后编辑（update）——MUST 要求操作者授权范围包含该单的**调出分公司**（admin/全量授权豁免），不满足时返回 400；编辑路径按「编辑后单据的调出分公司在范围内」校验。流转单序列化器 MUST 输出 `canOperate` 只读字段（transfer 类型 = 范围含调出分公司，其余类型恒 true，无请求上下文时默认 true）；前端（PC 调拨列表/详情、移动端审批中心）MUST 按 `canOperate` 显隐写操作按钮——调入方视角不出现操作入口，详情查看不隐藏。

#### Scenario: 调入方审批被拒

- **WHEN** 数据范围仅含分公司 B 的审批人对一笔 from=A、to=B 的待审批调拨单调用 approve
- **THEN** 返回 400（调入方只读），单据状态不变、台账不动

#### Scenario: 调出方正常审批

- **WHEN** 数据范围含分公司 A（调出方）的审批人对同一单据调用 approve
- **THEN** 审批正常生效，台账按单据联动

#### Scenario: 调入方对调入单只读可见

- **WHEN** 数据范围仅含分公司 B 的用户查询流转单列表
- **THEN** from=A、to=B 的调拨单出现在其列表，序列化结果 `canOperate` 为 false；from=B 发起的调拨单 `canOperate` 为 true

#### Scenario: 前端按 canOperate 隐藏操作入口

- **WHEN** 调入方用户在 PC 调拨列表、单据详情或移动端审批中心查看 from=A、to=B 的待审批调拨单
- **THEN** 通过/驳回等写操作按钮不显示，详情入口仍可用

