# transfer-stock-link Specification

## Purpose
TBD - created by archiving change transfer-stock-link-and-recovery-split. Update Purpose after archive.
## Requirements
### Requirement: 领用出库审批后扣减库存
领用出库审批通过后，调出分公司的对应资产（资产编号+分公司匹配）数量 SHALL 按调拨数量扣减。

#### Scenario: 领用后库存下降
- **WHEN** 领用出库单（数量=3）审批通过
- **THEN** 调出分公司该资产数量减少 3，状态改为「使用中」（或数量为 0 时「已领完」）

### Requirement: 调拨审批后调出降调入增
调拨审批通过后，调出分公司资产数量 SHALL 扣减，调入分公司资产数量 SHALL 增加（同编号存在则累加、不存在则新建）。

#### Scenario: 调拨后两边库存变化
- **WHEN** 调拨单（数量=5，从 A 到 B）审批通过
- **THEN** A 分公司该资产数量 -5，B 分公司该资产数量 +5（或新建）

### Requirement: 回收独立为单独菜单板块
回收 SHALL 从「资产流转」菜单子项独立为一级菜单板块。

#### Scenario: 回收作为独立菜单
- **WHEN** 用户查看侧边导航
- **THEN** 「回收」作为独立一级菜单项，不在「资产流转」子菜单下

