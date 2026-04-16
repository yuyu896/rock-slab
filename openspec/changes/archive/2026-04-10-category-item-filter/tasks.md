## 1. 前端状态与联动逻辑

- [x] 1.1 在 Category.vue 中新增 `filterItemCategory` ref（默认空字符串）
- [x] 1.2 新增 `itemCategories` computed：基于 `allCategories` 生成二级分类选项。如果 `filterCategory` 有值则只显示对应一级下的二级分类，否则显示全部
- [x] 1.3 在 `watch([filterCategory, filterKeyword])` 中增加逻辑：`filterCategory` 变更时清空 `filterItemCategory`
- [x] 1.4 将 `filterItemCategory` 加入 watch 触发 `fetchCategories`（重置 page=1）
- [x] 1.5 在 `fetchCategories` 中传入 `物品分类: filterItemCategory.value || undefined`

## 2. 前端筛选器 UI

- [x] 2.1 在模板筛选区"资产类目"下拉后面新增"物品分类"下拉 `<select>`，绑定 `filterItemCategory`，选项由 `itemCategories` computed 提供

## 3. 验证

- [x] 3.1 选择物品分类后数据正确过滤
- [x] 3.2 切换资产类目后物品分类选项正确联动、已选值被清空
- [x] 3.3 不选物品分类时不影响筛选
