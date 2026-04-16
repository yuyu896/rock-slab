### Requirement: Teams management tab

系统 SHALL 在组织架构模块中提供"行政组"标签页，与"区域管理"、"分公司管理"同级。标签页中 SHALL 展示所有行政组的卡片列表，每张卡片显示组名、所属区域、组长、组员数量、状态。

#### Scenario: View teams list
- **WHEN** 用户点击"行政组"标签页
- **THEN** 系统 SHALL 通过 `GET /api/teams/` 获取所有行政组并以卡片网格形式展示

#### Scenario: Empty teams list
- **WHEN** 系统中没有行政组
- **THEN** 系统 SHALL 显示空状态提示

### Requirement: Create team from tab

标签页 SHALL 提供"新增行政组"按钮。点击后 SHALL 打开行政组表单弹窗，包含组名（必填）、所属区域（必填）、组长（可选）字段。保存时 SHALL 调用 `POST /api/teams/`。

#### Scenario: Create team successfully
- **WHEN** 用户填写组名、选择区域并点击"确定保存"
- **THEN** 系统 SHALL 调用 `POST /api/teams/` 创建行政组，刷新列表，显示成功提示

### Requirement: Edit team from tab

每张行政组卡片 SHALL 提供编辑按钮。点击后 SHALL 打开预填当前数据的表单弹窗。保存时 SHALL 调用 `PUT /api/teams/<id>`。

#### Scenario: Edit team successfully
- **WHEN** 用户修改组名并保存
- **THEN** 系统 SHALL 调用 `PUT /api/teams/<id>` 更新行政组，刷新列表

### Requirement: Delete team from tab

每张行政组卡片 SHALL 提供删除按钮。点击后 SHALL 显示确认对话框，确认后调用 `DELETE /api/teams/<id>`。

#### Scenario: Delete team successfully
- **WHEN** 用户确认删除
- **THEN** 系统 SHALL 调用 `DELETE /api/teams/<id>`，刷新列表

#### Scenario: Cancel delete
- **WHEN** 用户取消确认
- **THEN** 系统 SHALL 不发送请求，列表保持不变
