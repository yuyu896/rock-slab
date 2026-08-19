## Decisions

### 决策 1：表格固定高度 + sticky 表头
- `.table-container { max-height: calc(100vh - 340px); overflow-y: auto; overflow-x: auto; }`
- `.data-table thead th { position: sticky; top: 0; z-index: 1; }`
- 表头 sticky 让滚动时列名始终可见。

### 决策 2：操作按钮加大
- 操作列按钮（action-btn）在固定资产表内覆盖为更大样式：`padding: 8px 16px; font-size: 14px`。
- 图标 svg 加大到 18px。

## Open Questions
（暂无。）
