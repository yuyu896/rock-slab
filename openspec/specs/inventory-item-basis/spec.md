# inventory-item-basis Specification

## Purpose
TBD - created by archiving change asset-v2-p2-asset-retire. Update Purpose after archive.
## Requirements
### Requirement: 盘点明细以台账行为基准

盘点项（InventoryItem）与盘点记录（InventoryCheck）MUST 关联台账行（`stock` FK → AssetStock，分公司×品目），MUST NOT 关联已退役的 Asset。盘点任务生成明细时 MUST 以任务分公司范围内、选中类目的台账行为源（跳过三列全零的空行），应盘数量（expected_qty）MUST 取该台账行的在库数量。盘点提交（check）MUST 按 stock 定位（asset 编号经 分公司×品目 解析为台账行），未登记品目 MUST 拒绝。

#### Scenario: 生成盘点项来自台账

- **WHEN** 分公司 A 创建盘点任务并生成明细，台账含 品目 X（在库 5）、品目 Y（三列全零）
- **THEN** 生成 品目 X 一项（应盘 5），品目 Y 被跳过

#### Scenario: 按编号提交盘点

- **WHEN** 盘点人提交 编号 X / 实盘 4
- **THEN** 定位到 (任务分公司 × X) 台账行并记录实盘 4，差异留存不动台账

### Requirement: 存量盘点项迁移

Asset 退役迁移 MUST 把存量盘点项按 (任务分公司, 资产编号→品目) 解析到台账行并换挂 stock FK；解析不到对应台账行的盘点项及其盘点记录 MUST 删除并输出计数（该类行在台账口径下本不存在，属脏数据）。迁移后盘点历史报告的编号/名称 MUST 经 stock.item 联查正常回显。

#### Scenario: 存量项换挂台账行

- **WHEN** 迁移时某盘点项原关联 Asset（分公司 A × 编号 X）且台账存在对应行
- **THEN** 该盘点项换挂到该台账行，应盘数量与结果保留

#### Scenario: 解析不到的项被清理

- **WHEN** 某盘点项原关联 Asset 的编号在品目字典未登记
- **THEN** 该盘点项与其盘点记录被删除，迁移输出清理计数

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

