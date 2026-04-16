## ADDED Requirements

### Requirement: 摄像头扫码
ScanAsset.vue 和 MobileScan.vue SHALL 提供摄像头扫码功能，使用浏览器 `getUserMedia` API 打开摄像头，结合 `BarcodeDetector` API 实时识别一维码。不支持的环境自动降级为手动输入模式。

#### Scenario: 摄像头扫码识别资产
- **WHEN** 用户在移动端扫码页面点击"扫描"按钮
- **THEN** 系统打开摄像头，识别到一维码后自动填入资产编号并触发查询

#### Scenario: 浏览器不支持 BarcodeDetector
- **WHEN** 用户在不支持 BarcodeDetector 的浏览器中使用扫码功能
- **THEN** 系统隐藏摄像头按钮，显示"手动输入"输入框作为降级方案

### Requirement: 移动端通知列表页
系统 SHALL 新增移动端通知列表页面（/mobile/notifications），展示用户的所有通知（审批提醒、任务通知、抄送消息），支持未读/已读筛选和标记已读操作。

#### Scenario: 查看通知列表
- **WHEN** 用户在移动端点击通知铃铛图标
- **THEN** 跳转到通知列表页面，按时间倒序展示所有通知

#### Scenario: 标记通知已读
- **WHEN** 用户点击某条未读通知
- **THEN** 系统调用 `markNotificationRead` API 标记该通知为已读，更新未读计数

### Requirement: 移动端单据提交表单
移动端 SHALL 在 Home.vue 的"提交入库"快捷入口中提供采购入库表单，包含分公司选择、供应商、物品明细、备注等字段。

#### Scenario: 移动端提交入库单
- **WHEN** 用户在移动端填写入库表单并提交
- **THEN** 系统调用创建资产 API 提交入库单，显示成功提示

### Requirement: 修改密码 UI
系统 SHALL 在移动端 Profile.vue 和 PC 端提供修改密码功能，包含旧密码、新密码、确认新密码三个字段，提交后调用 `updatePassword` API。

#### Scenario: 修改密码成功
- **WHEN** 用户输入正确的旧密码和新密码（两次一致）并提交
- **THEN** 系统调用 `PUT /api/auth/password` 修改密码，显示成功提示，退出登录要求重新登录

#### Scenario: 新密码不一致
- **WHEN** 用户输入的新密码和确认密码不一致
- **THEN** 系统显示校验错误"两次密码输入不一致"，阻止提交

### Requirement: 组织架构区域负责人动态加载
Organization.vue 中区域编辑表单的"区域负责人"下拉选项 SHALL 动态从用户列表 API 加载，仅显示具有 supervisor 角色的用户。

#### Scenario: 选择区域负责人
- **WHEN** 用户编辑区域时打开负责人下拉框
- **THEN** 下拉选项从 `GET /api/users?role=supervisor` 动态加载，显示所有行政主管用户

### Requirement: 组织架构状态切换
Organization.vue 中区域、分公司、用户的列表 SHALL 提供启用/停用的开关控件（el-switch），切换后调用对应的 update API 更新状态。

#### Scenario: 停用分公司
- **WHEN** 用户在分公司列表中点击某分公司的状态开关（从启用切换为停用）
- **THEN** 系统调用 `PUT /api/branches/:id` 更新状态为 inactive，显示成功提示

#### Scenario: 启用已停用的用户
- **WHEN** 用户在用户列表中点击某用户的状态开关（从停用切换为启用）
- **THEN** 系统调用 `PUT /api/users/:id` 更新状态为 active，显示成功提示

### Requirement: 组织架构搜索筛选修复
Organization.vue 的关键词搜索和区域筛选 SHALL 实际过滤展示的数据列表。

#### Scenario: 关键词搜索区域
- **WHEN** 用户在搜索框中输入关键词
- **THEN** 区域、分公司、用户列表仅显示名称/编号/手机号包含关键词的项

#### Scenario: 按区域筛选分公司
- **WHEN** 用户选择某个区域作为筛选条件
- **THEN** 分公司和用户列表仅显示属于该区域的数据

### Requirement: Dashboard 角色权限视图
Dashboard.vue SHALL 根据当前用户角色传递不同参数给统计 API：超级管理员/行政经理不传 scope 参数（全集团数据），行政主管传 regionId，行政组长/行政专员传 branchId。

#### Scenario: 行政专员查看看板
- **WHEN** 行政专员登录后查看 Dashboard
- **THEN** 统计数据仅显示其所属分公司的资产数据

#### Scenario: 行政主管查看看板
- **WHEN** 行政主管登录后查看 Dashboard
- **THEN** 统计数据仅显示其管辖区域内所有分公司的资产数据

### Requirement: 报表分类分布图数据填充
Reports.vue SHALL 调用报表 API 获取分类维度统计数据，填充分类分布环形图。

#### Scenario: 查看分类分布图
- **WHEN** 用户进入报表页面
- **THEN** 分类分布环形图显示各资产类目的数量占比数据

### Requirement: 报表月度趋势图数据填充
Reports.vue SHALL 获取月度资产变动趋势数据（入库/出库/调拨），填充月度趋势柱状图。

#### Scenario: 查看月度趋势图
- **WHEN** 用户进入报表页面
- **THEN** 月度趋势图显示近 12 个月的入库、出库、调拨数量柱状图

### Requirement: 报表变动明细 Tab 数据切换
Reports.vue 的"变动明细" Tab 切换后 SHALL 调用 `getTransferReport` API 获取变动明细数据并展示。

#### Scenario: 切换到变动明细 Tab
- **WHEN** 用户在报表页面点击"变动明细" Tab
- **THEN** 表格数据源切换为流转变动明细列表
