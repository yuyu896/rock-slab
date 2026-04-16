## Why

资产分类模块筛选区当前只有"资产类目"（一级分类）下拉和关键词搜索，缺少"物品分类"（二级分类）的筛选。用户无法快速按二级分类过滤数据，需要逐页查找。后端 CategoryFilterSet 已支持 `物品分类` 过滤参数，只需补齐前端筛选 UI 和联动逻辑。

## What Changes

- 前端 Category.vue 筛选区新增"物品分类"下拉选择器
- 物品分类选项与资产类目联动：选择一级分类后，二级分类只显示对应项；未选一级分类时显示全部二级分类
- 新增 `filterItemCategory` ref 存储选中值
- `fetchCategories` 传入 `物品分类` 参数，后端服务端过滤
- 一级分类变更时自动重置物品分类选择

## Capabilities

### New Capabilities
- `category-item-filter`: 资产分类页面新增物品分类（二级分类）筛选器，支持与资产类目联动

### Modified Capabilities

## Impact

- **前端**: `frontend/src/views/Category.vue` 新增筛选器 UI 和联动逻辑
- **前端 API**: `frontend/src/api/categories.ts` 的 `getCategories` 新增 `物品分类` 参数（已支持）
- **后端**: 无需修改，`CategoryFilterSet` 已支持 `物品分类` 过滤
