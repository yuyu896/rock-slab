# inventory-item-basis 增量

## RENAMED Requirements

### Requirement: 部门实例盘点
- FROM: `部门实例盘点`
- TO: `实例盘点（全分公司）`

## MODIFIED Requirements

### Requirement: 实例盘点（全分公司）

盘点任务 SHALL 以显式 `kind` 字段表达盘点方式（stock=台账盘点 / instance=实例盘点，默认 stock）；`is_instance_inventory` MUST 基于 kind 判定（MUST NOT 再以 department 是否为空推断）。实例盘任务创建时 MUST NOT 要求或接受部门维度（存量任务的 department 值保留作档案展示，不参与任何逻辑）。开始盘点时生成**全分公司** `状态=在用` 实例的快照清单（InventoryInstanceItem，task×instance 唯一），可选类目过滤（按资产类目）；核对动作 MUST 逐台进行（found=true→matched / found=false→missing，重复核对以最后一次为准并累计次数），清单 MUST 按使用人分组展示，计数单位为"台"。数量管理品目 MUST NOT 出现实例盘清单（无实例档案层）。台账盘点任务（kind=stock）MUST NOT 生成实例清单。重复盘点规则（last/accumulate）MUST NOT 作用于实例盘（一台一勾）。存量迁移 MUST 把 department 非空的老任务回填为 kind=instance。

#### Scenario: 生成全公司实例清单

- **WHEN** 分公司 A 创建实例盘任务（不选部门）并开始，A 在用实例 5 台（分布于两个部门，品目 X），另有品目 Y（数量管理）库存若干
- **THEN** 清单为 5 行实例项（各含内部编号/使用人/所属部门），品目 Y 不出现

#### Scenario: 类目过滤可选

- **WHEN** 创建实例盘任务时选择资产类目「固定」
- **THEN** 清单仅含资产类目为「固定」的在用实例

#### Scenario: 创建不再校验部门

- **WHEN** 创建实例盘任务的请求不携带 department（或携带空值）
- **THEN** 创建成功，任务 kind=instance、department 为空

#### Scenario: 逐台核对

- **WHEN** 盘点人对某在用实例执行核对 found=true，对另一台 found=false
- **THEN** 前者 result=matched（记核对人与时间），后者 result=missing

#### Scenario: 存量任务回填

- **WHEN** 迁移执行时存在 department 非空的历史实例盘任务
- **THEN** 其 kind 回填为 instance，department 值保留，清单与状态不变
