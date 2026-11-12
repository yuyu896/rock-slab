## Why

品目分类数据混乱：用户在"物品分类"字段自由输入，导致同一类物品有多种表述（"办公设备""办公设备类""办公"），造成数据不一致。通过级联下拉改动，强制用户从受控列表选择，同时后端加 ChoiceField 验证，确保入库数据的一致性和规范性。

## What Changes

- 前端：物品分类从文本输入改为下拉选择，跟随资产类目联动（选定资产类目后，物品分类下拉仅显示该资产类目对应的有效分类）
- 后端：Category 模型的 item_category 字段加 choices 约束；CategorySerializer 改用 ChoiceField 验证；新增数据库迁移
- 常量：建立资产类目 → 物品分类的映射关系（ITEM_CATEGORIES_BY_ASSET_CATEGORY），置于 constants/index.ts
- API 端点：新增 `/api/categories/item-categories/` 按资产类目返回对应的物品分类列表

## Capabilities

### New Capabilities
- `category-item-cascading`: 前端物品分类下拉随资产类目联动，仅展示有效分类选项
- `category-validation-backend`: 后端对资产类目和物品分类进行 ChoiceField 验证，防止非法值

### Modified Capabilities
- `category-management`: 现有品目管理页面（新增/编辑分类）的物品分类字段从文本输入改为受控下拉

## Impact

- **前端**: CategoryCreate.vue、CategoryForm.vue（物品分类从 `<input type="text">` 改为 `<select>`，加级联逻辑）；constants/index.ts（新增映射常量）；API 调用层 api/categories.ts（新增获取物品分类列表的接口）
- **后端**: Category 模型字段约束更新；CategorySerializer 验证逻辑加强；新增数据库迁移
- **API**: 新增端点 GET /api/categories/item-categories/?asset_category=<value>
- **数据**：无破坏性改动，已有数据保持不变；仅约束新增/修改时的输入
