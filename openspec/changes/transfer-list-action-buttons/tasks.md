## 1. 间距

- [x] 1.1 `styles/action-buttons.css`：`.action-buttons` 去掉 `gap`，改用 `.action-btn + .action-btn { margin-left: 8px; }`（兼容未包裹的列表单元格场景，避免双重间距）

## 2. 按钮样式增强

- [x] 2.1 `.action-btn` 内边距 `4px 10px` → `6px 12px`，加 `line-height: 1.4`（更醒目的按钮感）；保留详情中性、通过(.approve)主色、驳回(.reject)危险色及各自 hover

## 3. 验证

- [x] 3.1 前端 `vue-tsc --noEmit` 通过（exit 0）
- [ ] 3.2 本地手动验证 4 个流转列表页：操作按钮间距合适、样式清晰可区分、hover 有反馈
