## Why

固定资产表页面在窄窗口下表格溢出被裁剪（`.table-container { overflow: hidden }` 导致水平溢出不可见）；且缺少标签打印功能（资产列表已有 AssetPrintDialog + 单行打印 + 批量打印，固定资产表没有）。

## What Changes

1. **布局修复**：`.table-container` 的 `overflow: hidden` 改为 `overflow-x: auto`，让宽表格在窄窗口下可水平滚动（不被裁剪）。
2. **标签打印**：给固定资产表添加标签打印功能——行内「打印标签」按钮 + 批量栏「打印标签」+ 打印弹窗，参考资产列表的 AssetPrintDialog 实现（可能复用或适配字段映射）。

## Capabilities

### New Capabilities
- `fa-layout-and-print`: 固定资产表布局自适应 + 标签打印。
