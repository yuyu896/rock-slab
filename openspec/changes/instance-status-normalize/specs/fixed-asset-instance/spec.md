# fixed-asset-instance Specification（修改）

## ADDED Requirements

### Requirement: 存量状态归一命令

系统 SHALL 提供 `normalize_instance_status` 管理命令，把旧导入时代混入的非法状态枚举按同义映射归一为四态：使用中→在用、空闲→回收库、空闲中→回收库、维修中→在用、已报废→退役。命令 MUST 默认预览（各非法状态条数与映射目标，不落任何改动），`--confirm` 时经实例服务层执行（写操作收敛 services，架构测试执法）。归一 MUST 只修改 当前状态 一列（分公司、台账、单据一概不动，不生成任何调整单）；MUST 幂等（全部合法后重跑输出无需归一）。

#### Scenario: 预览不落库

- **WHEN** 存在 3 条「使用中」实例，执行 `normalize_instance_status`
- **THEN** 输出「使用中 × 3 → 在用」，数据库无改动

#### Scenario: 确认归一

- **WHEN** 承上执行 `--confirm`
- **THEN** 3 条实例 当前状态 变为「在用」，分公司/台账/单据无任何变化

#### Scenario: 幂等重跑

- **WHEN** 归一完成后再次执行
- **THEN** 输出「全部实例状态均为合法四态，无需归一」，零改动
