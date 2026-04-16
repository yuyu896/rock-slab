# 可访问性：表单标签关联

所有表单输入控件必须有关联的标签元素，确保屏幕阅读器用户能够理解输入框的用途。

## ADDED Requirements

### Requirement: 表单输入必须有关联标签

所有表单输入控件（`<input>`, `<select>`, `<textarea>`）必须有通过 `for` 属性或隐式包装关联的 `<label>` 元素。

#### Scenario: 文本输入框标签关联
- **WHEN** 页面包含文本输入框
- **THEN** 输入框必须有一个 `<label>` 元素通过 `for` 属性关联到输入框的 `id`
- **AND** 标签文本清晰描述输入框的用途

#### Scenario: 下拉选择框标签关联
- **WHEN** 页面包含下拉选择框 `<select>`
- **THEN** 选择框必须有一个 `<label>` 元素通过 `for` 属性关联
- **AND** 标签文本描述选择框的选项类别

#### Scenario: 必填字段标识
- **WHEN** 表单字段为必填项
- **THEN** 标签必须包含视觉指示器（如星号 `*`）
- **AND** 使用 `aria-required="true"` 属性标记

### Requirement: 标签文本必须清晰可见

标签文本应当始终可见，不得使用 `display: none` 或 `visibility: hidden` 隐藏标签。

#### Scenario: 标签可见性
- **WHEN** 表单渲染完成
- **THEN** 所有标签文本必须对视力正常用户可见
- **AND** 标签与输入框的关联关系清晰

#### Scenario: 使用 placeholder 作为补充说明
- **WHEN** 输入框需要额外提示
- **THEN** `placeholder` 属性仅作为补充说明
- **AND** 不得用 `placeholder` 替代 `<label>`

### Requirement: 分组字段必须有标题

一组相关的表单字段（如地址字段组）必须使用 `<fieldset>` 和 `<legend>` 进行分组。

#### Scenario: 字段分组
- **WHEN** 表单包含多个相关字段（如省/市/区地址）
- **THEN** 必须使用 `<fieldset>` 包装这些字段
- **AND** 使用 `<legend>` 提供分组标题
