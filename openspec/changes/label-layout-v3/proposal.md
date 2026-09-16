# 提案：标签版式 V3——英文字段前缀、删除品目编号行

## Why

用户实机验收 V2 后定稿标签模板：每行带字段前缀（如 `SN：`），并将中文前缀统一替换为英文短标签（热敏纸小字号下英文更清晰、更省宽度）；品目编号行删除——内部编号（如 `A-a00008-BJ001-1`）本身含品目码前缀，信息无损失。

## What Changes

- **行集改五行**（V2 六行 → V3 五行）：
  1. `NO: <内部编号>`
  2. `SN: <序列号>`（空则整行隐藏）
  3. `ITEM: <品目名称>`
  4. `BRANCH: <分公司>`
  5. `VENDOR: <供应商>  DATE: <采购日期>`（同一行，两项皆空整行隐藏、单项空只留存在项）
- **前缀用英文短标签**：NO: / SN: / ITEM: / BRANCH: / VENDOR: / DATE:（全大写短词、统一带冒号、等宽）
- **首行混合字号**：前缀 `NO:` 用辅助级字号（2.6mm），内部编号保持 3.4mm 加粗——前缀不挤占主码宽度
- 打印 CSS 与 canvas（`LABEL_SPEC`）两侧同步；空值隐藏规则沿用

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `fa-layout-and-print`: 标签行集与文案格式变更——英文前缀五行模板、删除品目编号行、首行前缀与主码混合字号

## Impact

- 前端：`utils/labelImage.ts`（行集与前缀渲染）、`AssetPrintDialog.vue`（模板行与前缀 span 样式）
- 测试：`labelImage.test.ts`、`AssetPrintDialog.test.ts` 行集断言更新
- 无后端/数据变更
