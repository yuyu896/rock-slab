# write-authorization-scoping Delta

## ADDED Requirements

### Requirement: 流转单写操作归属（仅创建人与 admin）
流转单的 update / destroy / submit / resubmit / withdraw SHALL 仅允许单据创建人（`created_by`）与 admin 执行；审批（approve/reject）的权限口径不变（按 `approve_transfer` 操作码）。范围内其他用户对他人单据 SHALL 收到 403。

#### Scenario: 非创建人改删他人单据被拒
- **WHEN** 与单据同数据范围但非创建人（且非 admin）的用户尝试修改、提交或删除该单据
- **THEN** 系统返回 403，单据不变

#### Scenario: 创建人可改可重提
- **WHEN** 单据创建人编辑被驳回的草稿并重新提交
- **THEN** 操作正常执行（submit/resubmit/update 均放行）

#### Scenario: admin 接手不受限
- **WHEN** admin 修改或删除任意单据
- **THEN** 按既有状态规则执行（已生效单据禁删等不变），归属不构成限制

#### Scenario: 审批人不因归属被拦
- **WHEN** 持 `approve_transfer` 的非创建人审批单据
- **THEN** approve/reject 正常执行（归属校验不覆盖审批动作）

## MODIFIED Requirements

### Requirement: 敏感写 action 必须声明权限码

审批、入库、导入、批量删除等敏感写 action MUST 在 ViewSet 的 `required_operations` 中显式声明所需操作码，未声明的此类写 action 不得放行。业务发起类 action（流转 `purchase/assign/return/transfer/recovery`、资产 `create`）按产品设计对所有登录用户开放（员工申请领用 / 采购 / 登记资产），不要求 `manage_assets`，其数据范围由「写操作必须校验目标分公司在授权范围」约束。**盘点模块的写 action（create/update/destroy/start/check/check-instance/submit/recount/cancel/import-result）MUST 声明 `manage_assets`（approve/reject 维持 `approve_inventory`）**。

#### Scenario: 流转导入未授权被拒
- **WHEN** 一个无 `manage_assets` 授权的用户 `POST /api/transfers/import-excel`
- **THEN** 系统返回 403，不解析文件

#### Scenario: 业务发起对所有登录用户开放但受范围约束
- **WHEN** 一个已登录用户 `POST /api/transfers/transfer`（或 purchase / assign 等业务发起）或 `POST /api/assets/`
- **THEN** 接口不在权限层拒绝；若目标分公司超出其授权范围，由范围校验返回 400

#### Scenario: 无码用户建盘点被拒
- **WHEN** 仅有任命（数据范围非空）但无任何 OperationGrant 的用户 `POST /api/inventories/`（或 start/submit/cancel/import-result 等）
- **THEN** 系统返回 403，盘点任务不创建、不锁流转

#### Scenario: 持码用户盘点正常
- **WHEN** 持 `manage_assets` 的分公司行政创建并执行盘点
- **THEN** 各写 action 正常（审批动作仍按 `approve_inventory`）

### Requirement: 写操作必须校验目标分公司在授权范围
流转创建（`purchase/assign/return/transfer/recovery`）、盘点任务创建、台账调整单创建、台账增量导入（差异预览与确认两阶段）、流转 Excel 导入、固定资产实例批量维护 MUST 校验其 `from_branch` / `to_branch` / `branch` / 导入行所属分公司 / 实例所属分公司均在 `resolve_user_scope(request.user).branches` 内；admin 豁免。**调拨（transfer 类型）为例外：创建、编辑与删除仅校验调出分公司（from_branch）在授权范围内，调入分公司不要求授权**（修订 3.1：跨范围调拨由单边发起，台账完整性由单据留痕与对账兜底）。其余类型维持全部分公司校验。**用户管理（create/update）提交的目标分公司 MUST 亦在操作者授权范围内（admin/全部数据豁免）。实例批量维护中 `branch` 为空的实例 MUST 报「未归属分公司」进 errors，不得静默穿过。**单对象接口任一应校验分公司越界时 MUST 返回 400 且不落库；批量导入中越权行 MUST 进 `errors`（提示分公司不在授权范围）、不进入差异预览、不可被确认入账或建单，合法行照常处理。台账增量导入的差异预览 MUST NOT 向无权用户返回范围外分公司的台账现值。

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

#### Scenario: 实例批量维护逐实例范围校验

- **WHEN** 数据范围仅含分公司 A 的持码用户提交 `batch-update`，ids 中混有分公司 B 的实例
- **THEN** 分公司 A 的实例照常更新；分公司 B 的实例进 `errors`（提示分公司不在授权范围），其供应商/规格/序列号等字段不被修改

#### Scenario: 调入方删除调拨单被拒

- **WHEN** 数据范围仅含调入分公司的用户对一笔 transfer 类型单据（草稿/待审批/已驳回）发起 DELETE
- **THEN** 系统返回 400（调入方分公司对此调拨单只读，仅调出方分公司可操作），单据保留；非调拨类型单据的删除规则不变

#### Scenario: 改挂范围外分公司被拒

- **WHEN** 数据范围仅含分公司 A 的持 `manage_users` 用户，把某用户（现属 A）的分公司改为 B
- **THEN** 系统返回 400，用户分公司不变

#### Scenario: 无分公司实例进 errors

- **WHEN** 持码用户提交 `batch-update`，ids 中含 `branch` 为空的实例
- **THEN** 该实例进 `errors`（提示未归属分公司），字段不被修改
