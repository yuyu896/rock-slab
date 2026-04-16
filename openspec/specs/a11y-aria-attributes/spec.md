# 可访问性：ARIA 属性

交互组件必须使用适当的 ARIA 属性提供语义信息，确保辅助技术用户能够理解和操作。

## ADDED Requirements

### Requirement: 模态框必须使用对话框语义

模态框（弹窗）组件必须使用正确的 ARIA 角色和属性。

#### Scenario: 对话框角色
- **WHEN** 模态框渲染到 DOM
- **THEN** 模态框容器必须具有 `role="dialog"` 属性
- **AND** 模态框容器必须具有 `aria-modal="true"` 属性

#### Scenario: 对话框标题关联
- **WHEN** 模态框包含标题
- **THEN** 标题元素必须有 `id` 属性
- **AND** 模态框容器必须有 `aria-labelledby` 属性引用标题 `id`

#### Scenario: 对话框描述关联
- **WHEN** 模态框包含描述文本
- **THEN** 描述元素必须有 `id` 属性
- **AND** 模态框容器应该有 `aria-describedby` 属性引用描述 `id`

### Requirement: 按钮必须传达其状态

交互按钮必须使用 ARIA 属性传达当前状态。

#### Scenario: 展开/折叠按钮
- **WHEN** 按钮控制内容的展开和折叠
- **THEN** 按钮必须有 `aria-expanded` 属性
- **AND** 展开时 `aria-expanded="true"`，折叠时 `aria-expanded="false"`

#### Scenario: 禁用按钮
- **WHEN** 按钮处于禁用状态
- **THEN** 必须使用 `disabled` 属性而非仅用 CSS 类
- **AND** 禁用按钮不应包含在 Tab 序列中

#### Scenario: 加载中按钮
- **WHEN** 按钮触发的操作正在进行中
- **THEN** 按钮必须有 `aria-busy="true"` 属性
- **AND** 按钮应该有 `disabled` 属性防止重复点击

### Requirement: 导航必须标识当前页面

主导航菜单必须标识用户当前所在的页面。

#### Scenario: 当前页面标识
- **WHEN** 用户在某个页面上
- **THEN** 对应的导航项必须有 `aria-current="page"` 属性
- **AND** 视觉样式应当与 `aria-current` 状态同步

### Requirement: 状态标签必须使用适当的语义

状态标签（如"在库"、"使用中"等）应当使用语义化标记。

#### Scenario: 状态标签语义
- **WHEN** 显示资产状态标签
- **THEN** 应当使用带有适当颜色的 `<span>` 元素
- **AND** 状态文本应当清晰可读
- **AND** 不应仅依赖颜色传达状态（需配合文本或图标）
