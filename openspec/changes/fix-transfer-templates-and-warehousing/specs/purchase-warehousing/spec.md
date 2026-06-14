## ADDED Requirements

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
