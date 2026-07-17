## 1. 表格固定高度滚动

- [ ] 1.1 `FixedAssetList.vue` `.table-container` 加 `max-height: calc(100vh - 340px); overflow-y: auto;`
- [ ] 1.2 `.data-table thead th` 加 `position: sticky; top: 0; z-index: 1;`

## 2. 操作按钮加大

- [ ] 2.1 `FixedAssetList.vue` scoped 样式覆盖 `.action-btn` 为 `padding: 8px 16px; font-size: 14px;`

## 3. 验证

- [ ] 3.1 vue-tsc 通过
- [ ] 3.2 本地手动：横向滚动条始终可见、操作按钮加大
