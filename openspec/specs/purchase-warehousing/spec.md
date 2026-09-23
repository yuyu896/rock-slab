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

采购入库创建页 SHALL 将「经办人」（Transfer 字段 `经办人`，原 `采购经办人` 重命名）预填为当前登录用户姓名；该字段 MUST 保持可修改、选填语义。提交时若值为空，服务端 SHALL 回填创建人姓名（四类单据统一口径，见 transfer-handler-field 能力）；提交校验 MUST NOT 因此增加必填限制。

#### Scenario: 打开创建页即预填

- **WHEN** 已登录用户打开采购入库创建页
- **THEN** 「经办人」显示该用户姓名，可直接提交

#### Scenario: 预填值可改可清空

- **WHEN** 用户将预填姓名清空或改为他人姓名后提交
- **THEN** 改为他人姓名时按输入保存；清空提交时由服务端回填创建人姓名
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

### Requirement: 待审批采购单创建人自助撤回

系统 SHALL 提供采购单「撤回」动作：仅当单据处于 `待审批` 状态、单据类型为采购入库、且操作者账号为单据的 `created_by`（创建账号）时可执行，撤回后单据回到 `草稿` 状态。创建人身份 MUST 依据账号外键判定，MUST NOT 依据姓名字符串比对。非创建人（含与创建人同名的账号）、非待审批状态（含已入库）、`created_by` 为空的存量单据的撤回请求 MUST 被拒绝并返回明确错误；撤回动作 MUST 记入审计日志且 MUST NOT 触碰台账数据。单据序列化结果 SHALL 包含 `canWithdraw` 布尔字段（服务端按当前请求者计算：采购单且待审批且请求者为创建账号），前端撤回入口 MUST 以该字段为准渲染。

#### Scenario: 创建人撤回待审批单

- **WHEN** 创建账号对自己处于待审批的采购单点击「撤回」并确认
- **THEN** 单据状态变为草稿，可编辑、可重新提交进入审批流

#### Scenario: 非创建人不可撤回

- **WHEN** 非创建账号（无论岗位、无论是否与创建人同名）对他人待审批采购单调用撤回
- **THEN** 后端返回错误拒绝，前端对该账号不显示撤回按钮（`canWithdraw` 为 false）

#### Scenario: 非待审批状态不可撤回

- **WHEN** 对草稿/已通过/已驳回/已入库状态的采购单调用撤回
- **THEN** 后端返回错误拒绝（已入库单据是对账事实源，纠错走既有机制）

#### Scenario: 无创建账号的存量单据不可撤回

- **WHEN** 对 `created_by` 为空的存量采购单（回填时重名或无匹配账号）调用撤回
- **THEN** 后端返回错误拒绝，前端不显示撤回按钮

#### Scenario: 存量单据回填创建账号

- **WHEN** 迁移对「创建人」字符串与账号姓名（或手机号）唯一匹配的存量单据执行回填
- **THEN** 该单据的 `created_by` 指向该账号，其创建账号此后可正常撤回；同名多账号或无匹配的单据保持为空

### Requirement: 草稿可编辑

采购单编辑接口 SHALL 接受 `已驳回` 与 `草稿` 两种状态的单据，编辑语义沿用既有规则（单头字段更新 + 明细整体替换、原子事务、行号重排）。

#### Scenario: 编辑草稿保存

- **WHEN** 用户编辑草稿状态的采购单并保存
- **THEN** 单头与明细按提交内容更新，状态保持草稿

### Requirement: 采购单 Excel 表格样式与行级供应商

采购单创建页与详情页的明细区 SHALL 以 Excel 式朴素表格呈现（表头行 + 数据行，行内编辑），明细行 SHALL 包含「供应商」列；表头（单据信息区）MUST NOT 再单独展示供应商字段。存量单据行级供应商为空时 SHALL 展示表头供应商值（继承规则）。

#### Scenario: 创建页按行录入供应商

- **WHEN** 用户在创建页添加两条明细并分别填写不同供应商
- **THEN** 明细表格每行独立保存各自供应商，表头无供应商输入

#### Scenario: 详情页表格展示供应商

- **WHEN** 用户查看采购单详情
- **THEN** 明细以表格呈现且含供应商列，表头信息区无供应商字段

#### Scenario: 存量单据供应商回退展示

- **WHEN** 查看行级供应商为空的历史采购单
- **THEN** 供应商列显示该单表头的供应商值

