## ADDED Requirements

### Requirement: Code128 条码生成
系统 SHALL 使用 JsBarcode 库为每个资产生成 Code128 格式的一维码，内容为资产编号。条码可渲染为 SVG 或 Canvas。

#### Scenario: 生成资产条码
- **WHEN** 系统展示资产标签或打印预览
- **THEN** 根据 `asset.资产编号` 字段生成 Code128 条码图像

### Requirement: 标签打印预览
AssetList.vue SHALL 提供"打印标签"功能，选中一个或多个资产后打开打印预览弹窗，展示资产编号条码、资产名称、分公司等信息。

#### Scenario: 打印单个资产标签
- **WHEN** 用户点击某资产的"打印标签"按钮
- **THEN** 打开打印预览弹窗，展示该资产的标签（含条码、编号、名称、分公司），提供"打印"按钮

#### Scenario: 批量打印资产标签
- **WHEN** 用户勾选多个资产后点击批量操作栏的"打印标签"按钮
- **THEN** 打开打印预览弹窗，展示所有选中资产的标签，每资产一个标签区域

### Requirement: 打印执行
标签打印预览弹窗 SHALL 提供"打印"按钮，调用 `window.print()` 触发浏览器打印对话框，仅打印标签区域内容。

#### Scenario: 执行打印
- **WHEN** 用户在打印预览弹窗中点击"打印"
- **THEN** 触发浏览器打印对话框，打印内容仅包含标签区域（通过 CSS @media print 控制）
