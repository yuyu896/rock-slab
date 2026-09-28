# 打印弹窗三段式布局 — 实施任务

## 1. 三段式布局改造

- [x] 1.1 `AssetPrintDialog.vue` CSS：`.modal-content` 去 `overflow-y: auto` 改 `display: flex; flex-direction: column`；`.modal-header`/`.modal-footer` 加 `flex-shrink: 0`；`.modal-body` 加 `flex: 1; min-height: 0; overflow-y: auto`
- [x] 1.2 打印态复位：`@media print` 中 `.modal-content` 补 `display: block`、`.modal-body` 补 `overflow: visible`（防 flex/overflow 容器打印分页裁剪，恢复与现状等价的块级流）

## 2. 测试守护

- [x] 2.1 源码契约断言：三段式（content flex column、body flex+overflow-y auto、header/footer flex-shrink 0）+ 打印态复位（content display block、body overflow visible）
- [x] 2.2 全量前端测试 `npm run test` 通过
- [x] 2.3 类型门禁 `npm run build` 通过

## 3. 收口

- [ ] 3.1 手验清单：勾选多页量标签打开弹窗——仅预览区滚动、纸型切换与打印/导出按钮常驻；A4 多页打印输出完整不裁剪；60×40 与导出视图回归
