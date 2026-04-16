## ADDED Requirements

### Requirement: 领用出库表单
系统 SHALL 在 Transfer.vue 中提供"领用出库"创建表单，包含以下字段：资产编号（必填，从分类中选择）、领用数量（必填）、领用人（必填）、所属部门（可选）、出库日期（默认当天）、备注（可选）。表单提交后调用 `assignAsset` API 创建待审批单据。

#### Scenario: 提交领用出库单
- **WHEN** 用户填写完领用出库表单并点击"提交"
- **THEN** 系统调用 `POST /api/transfers/assign` 提交单据，列表刷新显示新单据（状态为"待审批"），显示成功提示

#### Scenario: 领用出库表单校验失败
- **WHEN** 用户未填写必填字段就提交领用出库表单
- **THEN** 系统显示校验错误信息，阻止提交

### Requirement: 归还表单
系统 SHALL 在 Transfer.vue 中提供"归还"创建表单，包含：资产编号（必填）、归还数量（必填）、归还日期（默认当天）、备注（可选）。提交后调用 `returnAsset` API。

#### Scenario: 提交归还单
- **WHEN** 用户填写完归还表单并点击"提交"
- **THEN** 系统调用 `POST /api/transfers/return`，列表刷新，显示成功提示

### Requirement: 调拨表单
系统 SHALL 在 Transfer.vue 中提供"调拨"创建表单，包含：资产编号（必填）、调出分公司（必填）、调出部门（可选）、调入分公司（必填）、调入部门（可选）、调拨数量（必填）、调拨原因（可选）、调出/调入负责人、备注（可选）。提交后调用 `transferAsset` API。

#### Scenario: 提交调拨单
- **WHEN** 用户填写完调拨表单并点击"提交"
- **THEN** 系统调用 `POST /api/transfers/transfer`，列表刷新，显示成功提示

#### Scenario: 调拨表单调入调出分公司不能相同
- **WHEN** 用户在调拨表单中选择了相同的调出和调入分公司
- **THEN** 系统显示校验错误"调出与调入分公司不能相同"，阻止提交

### Requirement: 维修表单
系统 SHALL 在 Transfer.vue 中提供"维修"创建表单，包含：资产编号（必填）、维修原因（必填）、维修数量（必填）、备注（可选）。提交后调用 `repairAsset` API，资产状态变更为"维修中"。

#### Scenario: 提交维修单
- **WHEN** 用户填写完维修表单并点击"提交"
- **THEN** 系统调用 `POST /api/transfers/repair`，列表刷新，显示成功提示

### Requirement: 报废表单
系统 SHALL 在 Transfer.vue 中提供"报废"创建表单，包含：资产编号（必填）、报废原因（必填）、报废数量（必填）、备注（可选）。提交后调用 `scrapAsset` API，审批通过后资产状态变更为"报废"。

#### Scenario: 提交报废单
- **WHEN** 用户填写完报废表单并点击"提交"
- **THEN** 系统调用 `POST /api/transfers/scrap`，列表刷新，显示成功提示

### Requirement: 流转 Tab 分类视图
Transfer.vue SHALL 提供 Tab 页签将流转记录按类型分类展示：全部、领用出库、归还、调拨、维修、报废。每个 Tab 仅显示对应类型的记录。

#### Scenario: 切换流转类型 Tab
- **WHEN** 用户点击"调拨" Tab
- **THEN** 列表仅显示调拨类型的流转记录

### Requirement: 审批驳回操作
Transfer.vue 列表和详情 SHALL 提供驳回按钮，点击后弹出输入驳回原因的对话框，确认后调用 `rejectTransfer` API。

#### Scenario: 驳回流转单
- **WHEN** 审批人点击"驳回"按钮并输入驳回原因后确认
- **THEN** 系统调用审批 API（approved: false），单据状态变为"已驳回"，显示成功提示

#### Scenario: 驳回原因为空
- **WHEN** 审批人点击"驳回"但未输入原因
- **THEN** 系统阻止提交，提示"请输入驳回原因"

### Requirement: 流转详情查看
Transfer.vue SHALL 提供流转单据详情弹窗（el-dialog），展示单据所有字段、审批状态、审批人、审批时间等完整信息。

#### Scenario: 查看流转详情
- **WHEN** 用户点击流转记录的"查看详情"按钮
- **THEN** 弹出详情弹窗，展示该单据的完整信息
