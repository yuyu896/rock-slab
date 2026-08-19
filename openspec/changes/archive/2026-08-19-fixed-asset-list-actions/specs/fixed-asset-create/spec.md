## ADDED Requirements

### Requirement: Create button in header
固定资产表页面头部 SHALL 在最右侧显示"新增"按钮（primary 样式），仅具有资产管理权限的用户可见。

#### Scenario: Create button visible for authorized users
- **WHEN** 用户拥有资产管理权限（canManageAssets）
- **THEN** 页面头部最右侧显示绿色的"新增"按钮

### Requirement: Create form dialog
点击新增按钮后 SHALL 弹出表单弹窗，包含以下字段：
- 资产编号（必填）
- 资产名称（必填）
- 序列号（选填）
- 供应商（选填）
- 使用人（选填）
- 所属部门（选填）
- 当前状态（选填，下拉：在库/在用/空闲）
- 分公司（选填，下拉选择）
- 备注（选填，多行文本）

#### Scenario: Open create dialog
- **WHEN** 用户点击"新增"按钮
- **THEN** 弹出空白表单弹窗，标题为"新增固定资产"

#### Scenario: Submit with required fields only
- **WHEN** 用户仅填写资产编号和资产名称后点击确定
- **THEN** 系统调用创建接口，成功后关闭弹窗、显示成功提示、刷新列表

#### Scenario: Submit with validation error
- **WHEN** 用户未填写必填字段（资产编号或资产名称）就点击确定
- **THEN** 表单显示验证错误提示，不发送请求

#### Scenario: Create success
- **WHEN** 创建接口返回成功
- **THEN** 弹窗关闭，页面显示"创建成功"提示，固定资产列表自动刷新

#### Scenario: Create failure
- **WHEN** 创建接口返回错误
- **THEN** 弹窗保持打开，页面显示错误提示消息

#### Scenario: Cancel create
- **WHEN** 用户点击取消按钮或点击弹窗外部区域
- **THEN** 弹窗关闭，不发送任何请求
