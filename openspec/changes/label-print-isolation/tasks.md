# 任务：标签打印输出隔离

## 1. 组件改造（AssetPrintDialog.vue）

- [x] 1.1 弹窗模板包 `<Teleport to="body">`，打印根与 `#app` 平级；条码渲染逻辑不变，验证 Teleport 后 barcode 渲染正常
- [x] 1.2 组件 scoped 样式追加 `@media print`：overlay 转静态去遮罩、modal-content 去 max-height/overflow/边框、header/footer 隐藏、`.print-label` `break-inside: avoid`、配色改白底黑字灰边框固定值

## 2. 全局打印规则

- [x] 2.1 组件内非 scoped 样式块追加 `@media print`：`#app { display: none !important }`、`body` 白底、`@page { margin: 8mm }`（打印 CSS 随组件走，不动 global.css）

## 3. 测试与验证

- [x] 3.1 新增 `frontend/src/tests/views/AssetPrintDialog.test.ts`：Teleport 到 body（#app 之外）、标签条数与文案、「打印」按钮调用 window.print
- [x] 3.2 跑通 `npm run test`（FixedAssetList 既有打印用例不回归）与 `npm run build`（类型门禁）
- [x] 3.3 浏览器实测：打印预览仅含标签、多页标签完整、深色模式输出正常（本地 dev 环境）
