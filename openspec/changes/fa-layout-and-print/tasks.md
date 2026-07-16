## 1. 布局修复

- [ ] 1.1 `FixedAssetList.vue` `.table-container { overflow: hidden }` → `overflow-x: auto`

## 2. 标签打印

- [ ] 2.1 检查 AssetPrintDialog 字段需求；复用或适配（传入 FixedAsset 数据）
- [ ] 2.2 `FixedAssetList.vue`：行内加「打印标签」按钮 + 批量栏加「打印标签」+ 打印弹窗
- [ ] 2.3 `printSingleLabel(item)` + `handlePrintLabels()` 逻辑

## 3. 验证

- [ ] 3.1 vue-tsc 通过
- [ ] 3.2 本地手动：窄窗口表格可滚动；打印标签弹出正常
