# A4 三列成品纸版式 — 实施任务

## 1. A4 版式改造（仅 A4 通道）

- [x] 1.1 `AssetPrintDialog.vue`：纸型按钮文案「A4 双列」→「A4 三列」；`applyPageSize` A4 分支改 `@page { size: A4; margin: 15.5mm 6mm; }`
- [x] 1.2 `.paper-a4` 版式 CSS 重写：`.print-labels` 三列 `repeat(3, 63.8mm)`、`column-gap: 3mm`（预览行距 4mm）；卡片定死 `63.8mm × 38mm`（border-box、padding 1.5mm、overflow hidden）；内部行集/前缀/QR/字号复用 60×40 的 mm 规范（文字可用宽 42.3mm）
- [x] 1.3 打印态：`.paper-a4 .print-labels { row-gap: 0 }`（上下贴齐），`break-inside: avoid` 维持
- [x] 1.4 A4 纸型下弹窗加宽（`.print-modal.paper-a4 { max-width: 860px }`，60×40 仍 800px），`.paper-a4 .print-labels` 窄屏横向滚动兜底

## 2. 测试守护

- [x] 2.1 更新既有测试中按文案找按钮的 `'A4 双列'` → `'A4 三列'`；纸型切换记忆用例回归
- [x] 2.2 新增 A4 版式源码契约断言：三列 63.8mm、列距 3mm、卡片 63.8×38、@page 15.5mm 6mm、打印态 row-gap 0、60×40 版式块未被改动（守护通道边界）
- [x] 2.3 全量前端测试 `npm run test` 通过
- [x] 2.4 类型门禁 `npm run build` 通过

## 3. 收口

- [ ] 3.1 手验清单：A4 真机打印一页 21 枚对成品纸四角核对（骑格即调）；60×40 单签与导出图片回归确认未受影响；纸型切换/缩号/弹窗三段式回归
- [x] 3.2 更新运维口径记忆：A4 批量容量 14 枚/页 → 21 枚/页、成品 21 枚不干胶纸
