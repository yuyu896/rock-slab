## 1. 修复 RecoveryList 响应式布局

- [x] 1.1 在 `RecoveryList.vue` 的 `.transfer-page` 样式中添加 `min-width: 0`，打破 flex 最小宽度约束
- [x] 1.2 确认 `.table-container` 的 `overflow-x: auto` 在窄视口下正常工作（表格横向滚动）

## 2. 统一修复其他流转页面

- [x] 2.1 在 `PurchaseList.vue` 的 `.transfer-page` 样式中添加 `min-width: 0`
- [x] 2.2 在 `AssignList.vue` 的 `.transfer-page` 样式中添加 `min-width: 0`
- [x] 2.3 在 `TransferList.vue` 的 `.transfer-page` 样式中添加 `min-width: 0`

## 3. 验证

- [ ] 3.1 启动开发服务器，在回收页面打开 F12 DevTools，确认页面不溢出、表格可横向滚动
- [ ] 3.2 在采购、领用、调拨页面分别验证同样行为
- [ ] 3.3 关闭 DevTools 后确认页面恢复正常宽屏布局
