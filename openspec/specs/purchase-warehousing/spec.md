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

### Requirement: 创建页存为草稿入口

采购入库创建页 SHALL 提供「存为草稿」操作（与「提交审批」并列），以草稿状态保存当前表单内容；存草稿 MUST NOT 触发审批通知（既有通知过滤：仅待审批发通知）；草稿后续可编辑、可提交进入审批流。

#### Scenario: 存为草稿不发通知

- **WHEN** 用户填写创建页后点击「存为草稿」
- **THEN** 单据以草稿状态保存，审批人不收到任何通知

#### Scenario: 草稿从列表提交

- **WHEN** 草稿单在列表页点击「提交」
- **THEN** 状态转为待审批，审批人收到通知

### Requirement: 撤回后自动进入编辑

撤回操作成功后，详情页 SHALL 自动进入编辑态（无需用户再点「修改」）；编辑保存后的提交路径 MUST 沿用既有草稿语义。

#### Scenario: 撤回直达编辑

- **WHEN** 创建人在撤回确认弹窗点「撤回」且操作成功
- **THEN** 详情页直接呈现编辑表单，可修改后「保存并提交」

### Requirement: 采购列表草稿统计卡

采购入库列表统计区 SHALL 显示「草稿」数量卡，口径与既有统计卡一致（当前页计数）。

#### Scenario: 存在草稿时卡片显示数量

- **WHEN** 列表当前页含 2 张草稿单
- **THEN** 草稿卡显示 2

