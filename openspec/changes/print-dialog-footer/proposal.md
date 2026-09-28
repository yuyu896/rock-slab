# 打印弹窗三段式布局——操作按钮常驻（print-dialog-footer）

## Why

全选批量打印标签时（当前页上限 100 条，A4 版式预览约 7 屏），打印弹窗整个内容区滚动（`.modal-content { max-height: 90vh; overflow-y: auto }`），底部操作按钮（关闭/导出图片/打印）与纸型切换栏被推到滚动区最底端，用户需滚到底才够得着「打印」。

## What Changes

- 打印弹窗 `AssetPrintDialog` 改**三段式布局**：`.modal-content` 改 `flex column`（去掉整体 `overflow-y: auto`），header/footer `flex-shrink: 0` 常驻，`.modal-body` `flex: 1; overflow-y: auto` 独立滚动——仅标签预览区滚动，标题栏（纸型切换）与底部按钮常驻可见。
- **打印态复位**：`@media print` 中 `.modal-content` 恢复 `display: block`、`.modal-body` 解除 `overflow`（`visible`）——防 flex/overflow 容器在浏览器打印分页时的多页裁剪，恢复与现状等价的块级文档流输出。
- 源码契约测试守护（该测试文件已有 `?raw` 源码断言惯例）：三段式布局 + 打印态复位两组断言。

对齐项目既有惯例：`ApprovePreviewDialog` / `AdjustRecordsDialog` / `InventoryReport` 三个弹窗已是 header/body/footer 三段、仅 body 滚动的模式，打印弹窗是唯一异类，本次归队。其他整窗滚动的弹窗（CategoryImportDialog、CategoryForm）内容短无此痛点，不动。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `fa-layout-and-print`：标签打印弹窗布局要求——新增「弹窗底部操作按钮常驻」「打印态解除内容区滚动」两条场景。

## Impact

- `frontend/src/views/assets/AssetPrintDialog.vue`：仅 CSS（布局类 + `@media print` 复位），不动逻辑。
- `frontend/src/tests/views/AssetPrintDialog.test.ts`：新增源码契约断言。
- 不涉及后端与数据模型。提案审查两问：无信息双存、无台账数量变动，通过。
