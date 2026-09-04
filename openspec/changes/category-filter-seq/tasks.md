## 1. 后端筛选

- [x] 1.1 `CategoryFilterSet` 增「管理方式」过滤参数（field_name='management_type'，精确匹配），三档取值回归测试（quantity/instance/consumable 各命中、组合资产类目筛选）

## 2. 前端筛选与序号

- [x] 2.1 Category.vue 筛选栏增管理方式下拉（选项映射 MANAGEMENT_TYPE_LABELS，value 为枚举键），fetchCategories 透传参数，watch 联动重置分页
- [x] 2.2 表格视图首列加序号（(page-1)×pageSize+index+1，窄列样式）；卡片视图同步显示序号
- [x] 2.3 导出按钮参数补齐为四筛选全量透传（资产类目/物品分类/管理方式/关键词）

## 3. 测试与验收

- [x] 3.1 前端 vitest：品目页表头含序号列、分页连续序号断言（对齐 AssetSummary.test.ts 既有写法）
- [x] 3.2 后端 pytest 全量 + 前端 vitest 全量 + `npm run build` 类型门通过
- [x] 3.3 本地起服实测：三档筛选命中、组合筛选、翻页序号连续、导出参数携带（网络面板核对）
