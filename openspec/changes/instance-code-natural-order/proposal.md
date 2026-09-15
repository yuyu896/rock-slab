# 实例编号自然排序

## Why

实例列表默认按 `内部编号` 字符串字典序——尾段数字无补零，跨位数后乱序（生产实测：`-1, -10, -11, … -19, -2, -20…`），用户看到编号"跳来跳去"。正确预期是数字顺序 `-1, -2, … -9, -10, -11`。

## What Changes

- 实例列表（含导出）排序改为 `Length(内部编号), 内部编号`——同前缀下先短后长、同长字典序，合成恰为数字自然序；跨库（PG/SQLite）兼容，不改编号格式、不加派生列
- 非目标：编号格式不改（不补零）；模型 Meta.ordering 不动（其他引用处字符串序无碍，仅列表/导出视图收口）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `fixed-asset-instance`: 实例列表/导出排序要求——编号数字自然序

## Impact

- **后端**: `FixedAssetViewSet.get_queryset` 加 order_by 表达式；测试（跨位数顺序断言）
- 前端零改动（沿用 API 顺序）
