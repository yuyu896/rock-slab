# 提案：标签打印输出隔离

## Why

打印标签弹窗点「打印」直接调用 `window.print()`，但全站没有任何 `@media print` 样式：实际打印出来的是整个系统页面（侧边栏、顶栏、资产表格、弹窗遮罩与按钮），而不是标签本身；且弹窗容器 `max-height: 90vh; overflow-y: auto` 在打印时把超出一屏的标签裁剪掉。标签打印功能在输出环节不可用，属于 P0 缺陷。

## What Changes

- 打印弹窗内容通过 `Teleport` 挂到 `body` 下独立的打印根节点，与 `#app` 应用壳并列
- 新增打印媒体查询：`@media print` 下隐藏整个 `#app`，仅输出标签区域；解除弹窗滚动容器的 `max-height`/`overflow` 裁剪，标签随纸张自然分页
- 打印输出使用打印友好配色（白底、黑字、灰边框），不受深色模式影响；单个标签 `break-inside: avoid` 不跨页切断

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `fa-layout-and-print`: 「固定资产表标签打印」需求补充打印输出隔离的约定——打印结果仅含标签内容（不夹带侧边栏/表格/弹窗控件），多标签跨页时完整输出不被裁剪

## Impact

- 前端：`frontend/src/views/assets/AssetPrintDialog.vue`（Teleport 结构 + 打印样式）、`frontend/src/styles/`（全局 `@media print` 隐藏 `#app` 的规则）
- 新增测试：`frontend/src/tests/views/AssetPrintDialog.test.ts`
- 无后端/API/数据/依赖变更
