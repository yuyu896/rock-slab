## MODIFIED Requirements

### Requirement: 盘点明细以台账行为基准

盘点项（InventoryItem）与盘点记录（InventoryCheck）MUST 关联台账行（`stock` FK → AssetStock，分公司×品目），MUST NOT 关联已退役的 Asset。台账盘任务（kind=stock）生成明细时 MUST 以任务分公司范围内、选中类目、**management_type≠instance 且行总量（在库+在用+回收库合计）> 0** 的台账行为源（实例管理品目由实例盘专属覆盖，不进台账盘——见 inventory-scope-dispatch），应盘数量（expected_qty）MUST 取行总量；差异调整单固定扣在库数量列（库别概念下线，存量 stock_bin 仅历史兼容）。盘点提交（check）MUST 按 stock 定位（asset 编号经 分公司×品目 解析为台账行），未登记品目 MUST 拒绝。

#### Scenario: 生成盘点项来自台账（非实例品目）

- **WHEN** 分公司 A 创建台账盘任务并生成明细，台账含 品目 X（数量管理，总量 5）、品目 Y（数量管理，三列全零）、品目 Z（实例管理，总量 89）
- **THEN** 生成 品目 X 一项（应盘 5=总量），品目 Y 与 Z 被跳过（Y 零量、Z 属实例盘范围）

#### Scenario: 按编号提交盘点

- **WHEN** 盘点人提交 编号 X / 实盘 4
- **THEN** 定位到 (任务分公司 × X) 台账行并记录实盘 4，差异留存不动台账
