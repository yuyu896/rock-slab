# 实例规格取出生行本批规格

## Why

采购导入/页面填写的「规格型号」存在明细行 `本批规格`（记录性），但实例档案/生平的规格列显示的是品目字典规格（`item.specification`）——字典为空时实例规格空白（生产实证：本批规格 'OPPO' 已落行、品目规格空、实例规格显示空）。用户预期：填了规格型号，实例档案就能看到。

## What Changes

- 实例规格显示链改为 **出生行本批规格优先**：`FixedAssetSerializer.item_spec = 出生行.本批规格 or item.specification`（与 供应商/单价/采购日期 同一批出生行派生字段，决策 #8 同构）；台账（品目级）规格仍取字典不动
- 非目标：不回写品目字典（不同批次规格可不同，回填会互相覆盖污染字典）；台账/品目页不动

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `fixed-asset-instance`: 实例档案规格输出改为出生行本批规格优先

## Impact

- **后端**: `FixedAssetSerializer.item_spec` 改 SerializerMethodField（出生行派生）；测试
- 前端零改动（沿用 itemSpec 字段）
