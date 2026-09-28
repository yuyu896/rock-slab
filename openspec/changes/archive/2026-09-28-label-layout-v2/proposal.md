# 提案：标签版式调整 V2——分行、加字段、放大字号

## Why

用户在 M1 实机打印验收后提出三点排版反馈：①分公司与品目编号挤在同一行，信息层次不清；②标签缺供应商与采购日期，实物核对（对机、对采购批次）需要这两项；③现版式内容整体偏下、字号偏小，实机打印出来不够醒目。

## What Changes

- **分行**：辅助信息由「品目 编号 · 分公司」一行拆为两行——「品目 <资产编号>」+「分公司」
- **新增字段**：供应商、采购日期上签（同一行「<供应商> · <采购日期>」，两项皆空则整行隐藏；单项为空只显示存在的部分）
- **字号上调**（60×40 版式，两条通道同步）：内部编号 3.2→3.6mm、SN 2.8→3.0mm、品目名称 3.0→3.4mm、辅助行 2.4→2.6mm
- **垂直布局校正**：行距 0.6→0.5mm、行高系数 1.25→1.2，并加 0.4mm 上移校正抵消行盒下行空隙导致的视觉偏下；打印 CSS 与 canvas（`LABEL_SPEC`）两侧同参数同步
- `toPrintShape` 补传供应商、采购日期

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `fa-layout-and-print`: 「固定资产表标签打印」的标签内容与版式规格变更——辅助信息分行、新增供应商/采购日期（空值隐藏）、字号上调与垂直居中校正

## Impact

- 前端：`FixedAssetList.vue`（toPrintShape 补字段）、`AssetPrintDialog.vue`（60×40 版式 CSS 与文案行）、`utils/labelImage.ts`（LABEL_SPEC 字号/行距、buildLabelLines 行集、布局上移校正）
- 测试：`labelImage.test.ts`（行集/字号/几何断言更新）、`AssetPrintDialog.test.ts`（文案断言更新）
- 无后端改动（供应商/采购日期已在实例接口返回中）
