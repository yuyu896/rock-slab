# asset-freeze-readonly Specification

## Purpose
TBD - created by archiving change asset-v2-p1-contract. Update Purpose after archive.
## Requirements
### Requirement: Asset 写接口冻结
资产明细（Asset）的写接口 MUST 全部下线：创建、更新、部分更新、删除、批量删除返回 405；Excel 导入接口返回 410 并提示改走台账导入（经调整单）。查询接口（列表、详情、导出）MUST 保留，Asset 作为历史视图供追溯，物理退役在 P2 执行。

#### Scenario: 创建被拒
- **WHEN** 用户调用资产明细创建接口
- **THEN** 返回 405，无数据写入

#### Scenario: 列表仍可读
- **WHEN** 用户打开资产明细列表页
- **THEN** 历史数据正常展示，页面无新建/编辑/删除/导入入口

### Requirement: 流转审批不再写 Asset
五类流转单审批通过后，系统 MUST NOT 修改任何 Asset 记录的状态、数量或归属字段——联动全部由台账承接。Asset 表数据自此静止（冻结快照）。

#### Scenario: 领用审批后 Asset 不变
- **WHEN** 领用单审批通过
- **THEN** 台账在库/在用按矩阵变动，全部 Asset 记录无任何字段变化

### Requirement: 盘点降级为记录模式
盘点任务审核通过时，系统 MUST NOT 再直接修改 Asset 数量；实际数量与期望数量的差异 MUST 仅记录在盘点结果中。「差异生成调整单」的完全体在 P3 交付，期间需要修数时由持 `adjust_ledger` 者手工开调整单。

#### Scenario: 审核通过不改 Asset
- **WHEN** 盘点任务含差异项（期望 5、实际 3）并审核通过
- **THEN** 差异记录留存，相关 Asset 数量不变

### Requirement: 报表切换台账口径
统计报表的总览、按分公司、按状态、按类目聚合 MUST 从台账（AssetStock）取数：状态维度为在库/在用/回收库三列；购入金额 MUST 从采购单聚合（金额属单据层）。报表 MUST NOT 依赖已冻结的 Asset 表取数量事实。

#### Scenario: 报表随台账联动
- **WHEN** 领用单（数量 4）审批通过后用户查看报表
- **THEN** 对应分公司的在库合计 −4、在用合计 +4，与台账一致

#### Scenario: 购入金额来自采购单
- **WHEN** 用户查看总览报表的购入金额
- **THEN** 数值为已通过采购单金额之和，与 Asset 表无关

