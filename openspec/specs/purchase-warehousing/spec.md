# purchase-warehousing Specification

## Purpose
TBD - created by archiving change fix-transfer-templates-and-warehousing. Update Purpose after archive.
## Requirements
### Requirement: Purchase transfer has a warehousing step after approval
The system SHALL require that purchase transfers (action_type=purchase) go through a manual "warehousing" step after approval. The approval status flow for purchases SHALL be: 待审批 → 已通过 → 已入库.

#### Scenario: Warehousing button appears after approval
- **WHEN** a purchase transfer has `审批状态 = '已通过'`
- **THEN** the system SHALL display a "入库" action button on that record in the purchase list

#### Scenario: Warehousing button not shown for non-approved or non-purchase
- **WHEN** a transfer is not of type `purchase` OR its `审批状态` is not `已通过`
- **THEN** the system SHALL NOT display the "入库" action button

### Requirement: Warehousing API endpoint creates asset records
The system SHALL provide a `POST /api/transfers/{id}/warehouse` endpoint that creates or updates Asset records when a purchase transfer is warehoused.

#### Scenario: Successful warehousing
- **WHEN** an authorized user calls warehouse on a purchase transfer with `审批状态 = '已通过'`
- **THEN** the system SHALL create a corresponding Asset record (or update quantity if asset with same 资产编号 exists), set the transfer's `审批状态` to `已入库`, and set the Asset's `入库日期` to the current date

#### Scenario: Warehousing rejected for invalid state
- **WHEN** warehouse is called on a transfer that is not `purchase` type or `审批状态` is not `已通过`
- **THEN** the system SHALL return a 400 error with an appropriate message

#### Scenario: Warehousing rejected for already warehoused
- **WHEN** warehouse is called on a transfer already in `已入库` status
- **THEN** the system SHALL return a 400 error indicating the transfer is already warehoused

### Requirement: Transfer model supports new approval status
The Transfer model's `APPROVAL_CHOICES` SHALL include `('已入库', '已入库')` as a valid status, applicable only to purchase type transfers.

#### Scenario: Purchase transfer status transitions
- **WHEN** a purchase transfer is created, approved, and then warehoused
- **THEN** the status transitions SHALL be: 待审批 → 已通过 → 已入库

### Requirement: 采购经办人预填当前用户

采购入库创建页 SHALL 将「采购经办人」预填为当前登录用户姓名；该字段 MUST 保持可修改、可清空、选填语义，提交校验与后端存储 MUST NOT 因此变更。

#### Scenario: 打开创建页即预填

- **WHEN** 已登录用户打开采购入库创建页
- **THEN** 「采购经办人」显示该用户姓名，可直接提交

#### Scenario: 预填值可改可清空

- **WHEN** 用户将预填姓名清空或改为他人姓名后提交
- **THEN** 单据按用户实际输入保存（空值合法），与现状一致

