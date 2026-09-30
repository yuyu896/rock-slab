## ADDED Requirements

### Requirement: 盘点锁定期间台账导入确认必须被拒

台账增量导入的确认阶段（confirm）MUST 在应用差异前检查全部目标分公司是否存在锁定状态（in_progress / pending_review）的盘点任务：存在则 MUST 返回 400（code `INVENTORY_LOCKED`，错误信息聚合全部锁定分公司名），且 MUST NOT 应用任何差异。锁定状态集 MUST 与流转创建/审批路径共享同一常量（`INVENTORY_LOCKED_STATUSES`），三路（创建、审批、导入确认）口径一致。

#### Scenario: 盘点进行中导入确认被拒

- **WHEN** 某分公司存在 in_progress 盘点任务，用户对包含该分公司差异的导入文件执行确认
- **THEN** 返回 400 INVENTORY_LOCKED（信息含该分公司名），台账无任何变动

#### Scenario: 多分公司差异聚合报错

- **WHEN** 导入差异涉及两个分公司且均处于盘点锁定
- **THEN** 400 错误信息同时列出两个分公司名

#### Scenario: 盘点结束后导入恢复正常

- **WHEN** 盘点任务离开锁定状态后重新确认导入
- **THEN** 按既有原子性语义正常应用
