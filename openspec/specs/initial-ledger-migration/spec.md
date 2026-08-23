# initial-ledger-migration Specification

## Purpose
TBD - created by archiving change asset-v2-p1-contract. Update Purpose after archive.
## Requirements
### Requirement: 存量聚合分桶规则
台账存量迁移 MUST 以 Asset 表为源，按 (分公司, 资产编号) 分组、纯 Python 端聚合数量（MUST NOT 使用数据库特定聚合函数，如 min(uuid)——SQLite 测试全绿生产 PostgreSQL 失败的前科）。状态分桶规则：当前状态「在库」计入在库列；「使用中」「维修中」计入在用列；「报废」视为已出局，不计入任何列。

#### Scenario: 状态分桶聚合
- **WHEN** 分公司 A 的品目 X 有明细：在库×5（数量 5）、使用中×2（数量 2）、维修中×1（数量 1）、报废×1（数量 3）
- **THEN** 生成台账行在库 5、在用 3，报废数量不入账

### Requirement: 期初调整单
迁移 MUST 为每个聚合行生成一条期初调整单（is_initial 标记，事由「系统期初」），台账行由唯一写入口按期初单入账。对账公式由此 MUST 无需期初特例：台账列 == Σ单据流水，历史数据全部被期初单吸收；期初时刻之前的流转单 MUST NOT 参与对账重算。

#### Scenario: 期初单生成且对账零差异
- **WHEN** 迁移完成后立即执行 `check_ledger_consistency`
- **THEN** 全库零差异（期初单 + 此后单据重算值 == 台账值）

### Requirement: 预览清单与确认流
系统 SHALL 提供 `preview_ledger_migration` 预览命令，输出：资产编号不在品目字典的存量行（含相近编号建议）、状态分桶统计、与旧 AssetStock 台账的数量差异行、部门归一清单。迁移执行命令 MUST 在存在未登记编号时拒绝执行（先行补字典）；执行 MUST 以全量备份完成为前置条件。

#### Scenario: 未登记编号阻断迁移
- **WHEN** 预览发现品目「PC-07」未在字典登记，管理员直接执行迁移命令
- **THEN** 命令拒绝执行，列出未登记编号清单并建议补录或修正明细

#### Scenario: 与旧台账差异留档
- **WHEN** 某编号 Asset 聚合值为 12 而旧 AssetStock 行为 10
- **THEN** 预览清单输出该差异（源 12 / 旧台账 10），迁移以 Asset 聚合 12 为准入账，差异留档供审计
