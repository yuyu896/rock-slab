# 补录弹窗上下文信息补全

## Why

序列号补录弹窗当前只显示内部编号——补录人无法直观核对是哪台设备（品目/使用人/部门不明），易错录。序列化器已输出 itemName/使用人/departmentName，纯前端补展示。

## What Changes

- 补录弹窗在内部编号之下增加三行只读信息：**品目名称、使用人、部门**（空值显示 -）
- 非目标：补录输入字段不变（仍仅 序列号/备注）；后端零改动

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `fixed-asset-instance`: 补录弹窗上下文展示要求

## Impact

- **前端**: 仅 `FixedAssetList.vue` 补录弹窗模板三行
