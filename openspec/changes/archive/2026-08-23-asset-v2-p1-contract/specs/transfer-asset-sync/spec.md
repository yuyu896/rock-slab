## REMOVED Requirements

### Requirement: 领用审批通过后更新 Asset 状态
**Reason**: Asset 表冻结只读，领用联动目标改为台账（在库−N、在用+N）；直接写 Asset 是被废止的非对称联动病根。
**Migration**: 领用台账联动契约见 `document-ledger-sync` 能力；Asset 仅作历史视图。

### Requirement: 归还审批通过后更新 Asset 状态
**Reason**: 同上，归还联动目标改为台账（在用−N、在库+N）。
**Migration**: 见 `document-ledger-sync` 能力。

### Requirement: 调拨审批通过后更新 Asset 归属
**Reason**: 同上，调拨联动目标改为双边台账（调出在库−N、调入在库+N）。
**Migration**: 见 `document-ledger-sync` 能力。

### Requirement: 回收联动资产汇总台账库存
**Reason**: 「仅回收联动台账、其他四类 MUST NOT 联动」的非对称契约正是漂移病根；V2 改为五单全部对称联动，且回收按去向二分（入回收库/直接处置）而非单一扣减下限为零。
**Migration**: 五单对称联动矩阵与回收二去向契约见 `document-ledger-sync` 能力。

### Requirement: 回收联动资产明细数量
**Reason**: Asset 冻结只读，回收不再扣减资产明细；数量事实唯一存放于台账。
**Migration**: 台账回收联动见 `document-ledger-sync` 能力；明细行保留作历史视图。

> 注：「回收删除固定资产实例记录」P1 维持现状（按内部编号物理删除），不在本 delta 中修改；P2 实例层接入时改为「状态→退役，档案永久保留」（设计书 5.3）。
