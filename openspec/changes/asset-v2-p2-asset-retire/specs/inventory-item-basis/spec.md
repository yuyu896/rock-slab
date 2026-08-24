# inventory-item-basis Specification（新增能力）

## ADDED Requirements

### Requirement: 盘点明细以台账行为基准

盘点项（InventoryItem）与盘点记录（InventoryCheck）MUST 关联台账行（`stock` FK → AssetStock，分公司×品目），MUST NOT 关联已退役的 Asset。盘点任务生成明细时 MUST 以任务分公司范围内、选中类目的台账行为源（跳过三列全零的空行），应盘数量（expected_qty）MUST 取该台账行的在库数量。盘点提交（check）MUST 按 stock 定位（asset 编号经 分公司×品目 解析为台账行），未登记品目 MUST 拒绝。

#### Scenario: 生成盘点项来自台账

- **WHEN** 分公司 A 创建盘点任务并生成明细，台账含 品目 X（在库 5）、品目 Y（三列全零）
- **THEN** 生成 品目 X 一项（应盘 5），品目 Y 被跳过

#### Scenario: 按编号提交盘点

- **WHEN** 盘点人提交 编号 X / 实盘 4
- **THEN** 定位到 (任务分公司 × X) 台账行并记录实盘 4，差异留存不动台账

### Requirement: 盘点差异为记录模式

盘点审核通过时系统 MUST NOT 修改台账数量（盘点记录与台账变动解耦）；差异 MUST 仅留存于盘点项结果。差异修数 MUST 经调整单（P3 交付差异自动生成调整单，期间由持 `adjust_ledger` 者手工开单）。

#### Scenario: 审核通过不改台账

- **WHEN** 盘点任务含差异项（应盘 5、实盘 3）并审核通过
- **THEN** 差异记录留存，台账在库数量不变

### Requirement: 存量盘点项迁移

Asset 退役迁移 MUST 把存量盘点项按 (任务分公司, 资产编号→品目) 解析到台账行并换挂 stock FK；解析不到对应台账行的盘点项及其盘点记录 MUST 删除并输出计数（该类行在台账口径下本不存在，属脏数据）。迁移后盘点历史报告的编号/名称 MUST 经 stock.item 联查正常回显。

#### Scenario: 存量项换挂台账行

- **WHEN** 迁移时某盘点项原关联 Asset（分公司 A × 编号 X）且台账存在对应行
- **THEN** 该盘点项换挂到该台账行，应盘数量与结果保留

#### Scenario: 解析不到的项被清理

- **WHEN** 某盘点项原关联 Asset 的编号在品目字典未登记
- **THEN** 该盘点项与其盘点记录被删除，迁移输出清理计数
