## Why

当前系统 Asset 表是「品目级别」的库存管理——一条记录代表一类资产（如"ThinkPad T14"），用「数量」字段表示有多少台。但实际业务中，电脑等固定资产需要追踪到每一台实物：哪台在谁手上、序列号是什么、是空闲还是在用。现有模型无法满足这个需求。

## What Changes

- 新增 `FixedAsset` 模型（资产实例表），一条记录 = 一台实物
- FixedAsset 通过 `资产编号` 关联到 Asset（品目），保留独立序列号、供应商、使用人、状态等字段
- FixedAsset 数量通过信号自动同步到 Asset.数量（在库/在用计数）
- 前端固定资产表页面（已创建 `/fixed-assets`）改为展示 FixedAsset 实例数据
- 资产列表页面保持不变，只显示品目级别的库存数量汇总

## Capabilities

### New Capabilities
- `fixed-asset-instance`: 固定资产实例模型、API、前端页面及库存同步机制

### Modified Capabilities
（无已有 spec 需要修改）

## Impact

- **后端新增**: `FixedAsset` 模型、序列化器、ViewSet、数据库迁移
- **后端修改**: Asset 模型的数量字段改为由 FixedAsset 实例自动计算同步
- **前端修改**: `FixedAssetList.vue` 改为调用新 API，支持实例级别的 CRUD 和筛选
- **数据迁移**: 需将现有 Asset 中 资产类目='固定' 的记录拆分为 FixedAsset 实例
