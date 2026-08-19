## ADDED Requirements

### Requirement: 流转审批在事务中原子完成

`TransferViewSet.approve`（及同类审批动作）SHALL 在单个 `transaction.atomic()` 块内完成"审批状态写库 + 资产状态同步"。事务内任何步骤失败 SHALL 回滚全部变更，MUST NOT 留下"审批已通过但资产未更新"的中间态。

#### Scenario: 审批过程中资产同步失败

- **WHEN** 审批已通过但随后的资产状态同步抛出异常
- **THEN** 审批状态写库也被回滚，流转单保持"待审批"，资产状态不变

#### Scenario: 重复提交审批

- **WHEN** 同一流转单的审批被并发或重复提交两次
- **THEN** 资产状态同步 SHALL 只生效一次，MUST NOT 出现数量或状态被重复累加

### Requirement: 库存数量调整使用行锁

盘点审核调整资产库存（`_adjust_inventory` 及同类）SHALL 使用 `select_for_update()` 对相关资产行加锁后再更新，并 SHALL 使用 `update(数量=F('数量') + diff)` 这类数据库端原子更新，MUST NOT 在 Python 端"读-改-写"逐条 `save`。盘点库存调整 SHALL 在 `transaction.atomic()` 内执行（`select_for_update` 方能生效）。

#### Scenario: 盘点与采购入库并发

- **WHEN** 盘点审核调整某资产数量的同时，另一请求对该资产执行采购入库累加
- **THEN** 两次更新均完整落库，MUST NOT 发生丢失更新

#### Scenario: 生成序号/内部编号的并发

- **WHEN** 两个采购入库请求并发为资产生成序号/内部编号
- **THEN** 生成的序号 SHALL 不冲突（通过加锁计数或数据库约束保证），MUST NOT 因 `count()+1` 竞态产生重复值
