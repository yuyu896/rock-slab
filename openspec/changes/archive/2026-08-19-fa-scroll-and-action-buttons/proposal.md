## Why

固定资产表两处 UI 瑕疵：
1. **滚动条不可见**：表格很多列，横向滚动条在表格最底部，必须先纵向滚到底才能拖动——应让表格在固定高度内滚动，横向滚动条始终可见。
2. **操作按钮太小**：编辑/删除/打印按钮用小号 `action-btn`，点击不方便，应加大到与资产列表一致。

## What Changes

1. **表格固定高度滚动**：`.table-container` 加 `max-height: calc(100vh - 340px)` + `overflow-y: auto`，表头 `position: sticky; top: 0`，让横向滚动条始终可见。
2. **操作按钮加大**：操作列按钮 padding/字号加大（从 6px 12px/12px → 8px 16px/14px），与资产列表操作按钮一致。

## Capabilities

### New Capabilities
- `fa-scroll-and-action-buttons`: 固定资产表滚动条始终可见 + 操作按钮加大。
