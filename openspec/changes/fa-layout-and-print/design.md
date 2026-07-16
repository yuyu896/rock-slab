## Context
- FixedAssetList `.table-container { overflow: hidden }` → 宽表格被裁剪，窄窗口下不可滚动。
- AssetList 有 AssetPrintDialog（props: assets[], visible）+ 行内 printSingleLabel + 批量 handlePrintLabels。
- FixedAssetList 已有编辑弹窗（el-dialog），但无打印。
- FixedAsset 字段（资产编号/资产名称/分公司/内部编号/序列号）与 Asset 类似，AssetPrintDialog 有复用可能。

## Decisions

### 决策 1：overflow-x: auto
- `.table-container { overflow: hidden }` → `overflow-x: auto`（保留 overflow-y: hidden）。

### 决策 2：复用/适配 AssetPrintDialog
- 优先复用 AssetPrintDialog——传入 FixedAsset 的 selectedIds 对应数据，字段映射到打印模板期望的格式。
- 若字段差异大（内部编号/序列号 vs 资产编号），新建 FixedAssetPrintDialog。

## Open Questions
1. 打印弹窗复用还是新建？默认尝试复用（最小改动），字段差异大则新建。
