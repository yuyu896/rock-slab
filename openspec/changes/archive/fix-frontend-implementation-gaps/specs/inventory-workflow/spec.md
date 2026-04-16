## ADDED Requirements

### Requirement: 创建盘点任务
Inventory.vue SHALL 提供"新建盘点任务"表单，包含：任务名称（必填）、盘点分公司（下拉选择，可为空表示全部）、盘点分类（下拉选择，可为空表示全部）、漏盘规则（下拉：保持不变/清零处理，默认保持不变）、重复盘点规则（下拉：以最后一次为准/累计数量，默认以最后一次为准）。提交后调用 `createInventoryTask` API。

#### Scenario: 创建指定分公司的盘点任务
- **WHEN** 用户填写任务名称、选择分公司和分类、选择漏盘和重复规则后点击"创建"
- **THEN** 系统调用 `POST /api/inventories` 创建任务，任务列表刷新，新任务状态为"待盘点"

#### Scenario: 创建全部分公司的盘点任务
- **WHEN** 用户不选择分公司和分类（留空）
- **THEN** 系统创建一个覆盖全部分公司和分类的盘点任务

### Requirement: 开始盘点
用户点击"开始盘点"后 SHALL 调用 `startInventory` API 将任务状态从"待盘点"变为"盘点中"。

#### Scenario: 启动待盘点的任务
- **WHEN** 用户在"待盘点"任务卡片上点击"开始盘点"
- **THEN** 系统调用 `POST /api/inventories/:id/start`，任务状态变为"盘点中"，可跳转到扫描视图

### Requirement: 盘点执行（扫码/手动录入）
盘点扫描视图 SHALL 提供资产编号输入框，支持扫码枪输入和手动输入。输入资产编号后查询对应资产，展示账面数量，用户确认实际数量后调用 `checkInventoryItem` API 记录盘点结果。

#### Scenario: 扫码盘点资产
- **WHEN** 用户在盘点扫描视图中输入资产编号并确认
- **THEN** 系统查询该资产信息，弹出确认对话框显示账面数量和实际数量输入框

#### Scenario: 确认盘点数量
- **WHEN** 用户在确认对话框中输入实际数量并点击确认
- **THEN** 系统调用 `POST /api/inventories/:id/check` 提交盘点记录，进度更新，最近盘点列表刷新

#### Scenario: 盘盈情况
- **WHEN** 实际数量大于账面数量
- **THEN** 系统标记结果为"盘盈"，显示盘盈提示

#### Scenario: 盘亏情况
- **WHEN** 实际数量小于账面数量
- **THEN** 系统标记结果为"盘亏"，显示盘亏提示

### Requirement: 提交审核
盘点执行完成后 SHALL 提供提交审核按钮，调用 `submitInventory` API 将任务状态从"盘点中"变为"待审核"。

#### Scenario: 提交盘点结果审核
- **WHEN** 用户在盘点扫描视图中点击"完成盘点"按钮
- **THEN** 系统调用 `POST /api/inventories/:id/submit`，任务状态变为"待审核"，显示成功提示

### Requirement: 审批通过
行政主管 SHALL 可以在盘点任务详情中点击"审批通过"，调用 `approveInventory` API 将状态变为"已完成"。

#### Scenario: 审批通过盘点结果
- **WHEN** 行政主管在"待审核"任务上点击"审批通过"
- **THEN** 系统调用 `POST /api/inventories/:id/approve`，任务状态变为"已完成"，库存自动调整

### Requirement: 审批驳回
行政主管 SHALL 可以驳回盘点结果，输入驳回原因后调用 `rejectInventory` API 将状态变为"已驳回"。

#### Scenario: 驳回盘点结果
- **WHEN** 行政主管点击"驳回"并输入驳回原因
- **THEN** 系统调用 `POST /api/inventories/:id/reject`，任务状态变为"已驳回"

### Requirement: 重新盘点
已驳回的任务 SHALL 提供"重新盘点"按钮，调用 `recountInventory` API 重置盘点数据后重新开始。

#### Scenario: 重新盘点被驳回的任务
- **WHEN** 用户在"已驳回"任务上点击"重新盘点"
- **THEN** 系统调用 `POST /api/inventories/:id/recount` 重置盘点项状态，任务回到"盘点中"

### Requirement: 作废盘点任务
待盘点/盘点中的任务 SHALL 提供"作废"操作，调用 `cancelInventory` API 将状态变为"已作废"。

#### Scenario: 作废盘点任务
- **WHEN** 用户点击"作废"按钮并确认
- **THEN** 系统调用 `POST /api/inventories/:id/cancel`，任务状态变为"已作废"

### Requirement: 盘点进度实时获取
盘点扫描视图 SHALL 定期调用 `getInventoryProgress` API 获取实时进度数据，更新进度条和统计信息。

#### Scenario: 查看盘点进度
- **WHEN** 用户进入盘点扫描视图
- **THEN** 系统调用 `GET /api/inventories/:id/progress` 获取进度数据，显示已盘/未盘/盘盈/盘亏数量

### Requirement: 盘点报告查看
已完成/已驳回的任务 SHALL 提供"查看报告"功能，调用 `getInventoryReport` API 展示差异明细、盘盈盘亏统计、未盘点清单。

#### Scenario: 查看盘点报告
- **WHEN** 用户点击任务的"查看报告"按钮
- **THEN** 系统调用 `GET /api/inventories/:id/report` 获取报告数据，展示完整的盘点报告面板

### Requirement: 多人协作盘点展示
盘点扫描视图 SHALL 调用 `getInventoryChecks` API 展示各盘点人的盘点记录，显示盘点人姓名、盘点数量、盘点时间。

#### Scenario: 查看协作盘点记录
- **WHEN** 用户在盘点扫描视图中查看"盘点记录"区域
- **THEN** 系统调用 `GET /api/inventories/:id/checks` 获取所有盘点人的操作记录并按时间倒序展示
