## ADDED Requirements

### Requirement: 盘点锁定期间流转审批必须被拒

流转单审批（approve）在应用台账变动前 MUST 对联单两侧分公司（from_branch / to_branch，为空的分支自然跳过）复查盘点锁：任一分公司存在处于锁定状态（in_progress / pending_review）的盘点任务时，approve MUST 返回 400（code `INVENTORY_LOCKED`，文案与创建路径一致），且 MUST NOT 变动台账、MUST NOT 改变单据审批状态（保持待审批）。创建路径的盘点锁检查维持不变，两侧闸门对称。

#### Scenario: 盘点进行中审批采购单被拒

- **WHEN** 某分公司存在 in_progress 盘点任务，审批人 approve 一张调入该分公司的待审批采购单
- **THEN** 返回 400 INVENTORY_LOCKED，台账数量不变，单据仍为待审批

#### Scenario: 调拨单任一侧锁定均被拒

- **WHEN** 调拨单的调出分公司或调入分公司任一侧存在锁定状态盘点任务，审批人 approve 该调拨单
- **THEN** 返回 400 INVENTORY_LOCKED，台账与单据状态不变

#### Scenario: 盘点结束后审批恢复正常

- **WHEN** 盘点任务离开锁定状态（如已审批完成）后，审批人 approve 此前被拒的待审批单
- **THEN** 审批成功，台账按单据正常变动

#### Scenario: 无关分公司的盘点不影响审批

- **WHEN** 盘点任务属于与单据无关的第三方分公司
- **THEN** approve 正常进行
