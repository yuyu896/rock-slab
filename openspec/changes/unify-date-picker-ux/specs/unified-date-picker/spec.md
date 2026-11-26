## ADDED Requirements

### Requirement: 单据日期选择器使用 Element Plus 组件
所有单据创建和编辑页面的日期输入框 SHALL 使用 Element Plus 的 `el-date-picker` 组件，而非原生 HTML5 `<input type="date">`。

#### Scenario: 用户点击日期输入框任意位置
- **WHEN** 用户点击日期输入框的任意区域（不仅是图标）
- **THEN** 系统 SHALL 弹出日期选择面板

#### Scenario: 日期格式保持 YYYY-MM-DD
- **WHEN** 用户选择日期后
- **THEN** 组件 SHALL 输出 `YYYY-MM-DD` 格式的字符串（与原生 input type="date" 一致）

#### Scenario: 样式与 Element Plus 组件一致
- **WHEN** 页面渲染时
- **THEN** 日期选择器 SHALL 使用 Element Plus 默认样式
- **AND** SHALL 与同页面的其他 Element Plus 表单组件（输入框、下拉框）保持视觉一致性

### Requirement: 覆盖所有单据相关日期输入
以下页面的日期输入 SHALL 全部替换为 `el-date-picker`：
- 采购入库单创建/编辑页面
- 领用出库单创建/编辑页面
- 回收单创建/编辑页面
- 调拨单创建/编辑页面（如存在）
- 调整记录对话框
- 固定资产列表筛选
- 回收台账筛选
- 采购详情页面（如有日期输入）

#### Scenario: 采购入库单日期选择
- **WHEN** 用户在采购入库单页面选择"调拨日期"
- **THEN** 系统 SHALL 使用 `el-date-picker` 组件
- **AND** SHALL 支持点击输入框任意位置弹出日期选择器

#### Scenario: 筛选面板日期选择
- **WHEN** 用户在固定资产列表或回收台账使用日期范围筛选
- **THEN** 系统 SHALL 使用 `el-date-picker`（type="daterange" 或单独 type="date"）
- **AND** SHALL 保持与 FilterPanel 组件的现有行为一致

### Requirement: 保持现有业务逻辑不变
日期组件替换 SHALL NOT 修改任何业务逻辑、验证规则或数据处理流程。

#### Scenario: 日期验证规则不变
- **WHEN** 用户提交包含日期的单据
- **THEN** 系统 SHALL 应用与原实现相同的日期验证规则
- **AND** SHALL 保持原有的错误提示信息

#### Scenario: v-model 绑定不变
- **WHEN** 日期组件绑定到表单数据
- **THEN** v-model 绑定的字段名和数据结构 SHALL 与原实现保持一致

### Requirement: 深色模式支持
日期选择器 SHALL 在深色模式下正确显示，无样式错误。

#### Scenario: 深色模式下弹出日期选择器
- **WHEN** 系统处于深色模式且用户点击日期输入框
- **THEN** 弹出的日期选择面板 SHALL 使用深色主题
- **AND** SHALL 保持文本可读性和对比度符合无障碍标准
