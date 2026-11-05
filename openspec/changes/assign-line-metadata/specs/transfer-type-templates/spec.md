## MODIFIED Requirements

### Requirement: Assign import template uses dedicated columns

系统 SHALL 按原顺序生成 7 列领用导入模板：分公司、日期、资产编号、领用数量、使用人、领用部门、备注。品目名称通过资产编号关联品目字典取得，不单独设置“领用物品”列。使用人、领用部门和备注 MUST 映射到领用明细行；领用部门 MUST 按全集团唯一的部门名称解析到部门外键，不按分公司限定，解析失败 MUST 按行报错并指出分公司和部门。用途不属于领用字段。旧模板中的可选“用途”列 MUST 被忽略。领用导入 MUST NOT 将领用部门写入单头“调出部门”。缺少使用人或领用部门的行 MUST 拒绝。

#### Scenario: 下载领用模板
- **WHEN** 用户下载领用导入模板
- **THEN** 生成的 Excel 文件 MUST 按原顺序包含以下列：分公司、日期、资产编号、领用数量、使用人、领用部门、备注，且 MUST NOT 包含用途列

#### Scenario: 使用领用模板导入
- **WHEN** 用户导入领用模板的一行记录
- **THEN** 资产编号经品目字典校验并关联品目，数量、使用人、领用部门和备注映射至该行对应的领用明细，并创建 `action_type = assign` 的单据

#### Scenario: 领用行缺少使用人
- **WHEN** 导入行的使用人单元格为空
- **THEN** 系统按行拒绝该记录，不创建该行对应的单据明细

#### Scenario: 领用部门不在全集团部门字典中
- **WHEN** 导入行填写的部门名称不在全集团部门字典中
- **THEN** 系统按行拒绝并在错误中指出分公司和部门

#### Scenario: 导入部门不写入调出部门
- **WHEN** 用户导入包含领用部门的领用模板
- **THEN** 部门只写入明细行部门关联，单头“调出部门”不被赋值

### Requirement: Transfer model has fields for all template columns

Transfer MUST 保留采购模板所需的供应商、单价、总金额、需求部门和共享经办人字段。领用明细 MUST NOT 对外提供用途字段；领用用途输入、回显、导入、导出和序列化 MUST 停用。历史 `TransferLine.用途` 和共享单头 `Transfer.用途` 数据保留在数据库中，领用 API MUST NOT 暴露这些值；共享单头用途字段对其他单据类型的原有兼容行为保持不变。新建或编辑领用单的设备备注 MUST 保存在 `TransferLine.备注`；`Transfer.备注` 继续承载历史单据内容、通用审批意见及其他类型的单据备注。

#### Scenario: Purchase transfer stores all template fields
- **WHEN** 采购单通过导入或表单创建
- **THEN** 系统按既有契约保存供应商、单价、总金额、需求部门和经办人

#### Scenario: Assign transfer stores per-line fields
- **WHEN** 领用单通过导入或表单创建
- **THEN** 系统仅在每条 `TransferLine` 保存该行备注，且领用单响应和明细响应均不包含用途字段

## ADDED Requirements

### Requirement: 领用导出按明细字段输出设备信息

领用 Excel 导出 MUST 对每条明细分别输出其领用部门和备注，MUST NOT 输出用途列；领用部门累计统计 MUST 按明细行部门归集，且 MUST NOT 使用单头“调出部门”作为部门来源。其他类型的导出列及字段来源 MUST 保持不变。

#### Scenario: 导出同单不同部门和备注的明细
- **WHEN** 用户导出一张包含多条且领用部门、备注各异的领用单
- **THEN** 每个导出行的部门和备注分别与其对应明细一致，导出不含用途列，部门累计统计归入该明细的实际部门

#### Scenario: 调拨导出仍使用调出部门
- **WHEN** 用户导出调拨单
- **THEN** 调拨导出仍按调拨单头的“调出部门”输出，不受领用字段调整影响
