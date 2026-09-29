# write-authorization-scoping Delta

## MODIFIED Requirements

### Requirement: 写操作必须校验目标分公司在授权范围
流转创建（`purchase/assign/return/transfer/recovery`）、盘点任务创建、台账调整单创建、台账增量导入（差异预览与确认两阶段）、流转 Excel 导入、固定资产实例批量维护 MUST 校验其 `from_branch` / `to_branch` / `branch` / 导入行所属分公司 / 实例所属分公司均在 `resolve_user_scope(request.user).branches` 内；admin 豁免。**调拨（transfer 类型）为例外：创建、编辑与删除仅校验调出分公司（from_branch）在授权范围内，调入分公司不要求授权**（修订 3.1：跨范围调拨由单边发起，台账完整性由单据留痕与对账兜底）。其余类型维持全部分公司校验。单对象接口任一应校验分公司越界时 MUST 返回 400 且不落库；批量导入中越权行 MUST 进 `errors`（提示分公司不在授权范围）、不进入差异预览、不可被确认入账或建单，合法行照常处理。台账增量导入的差异预览 MUST NOT 向无权用户返回范围外分公司的台账现值。

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
