## 1. 所属部门下拉（固定列表）

- [x] 1.1 `constants` 新增 `DEPARTMENT_OPTIONS = ['行政部','财务部','人事部','业务部','其他']`
- [x] 1.2 `AssetCreatePage.vue`「所属部门」由 `<input>` 改 `<select>`，选项取自 `DEPARTMENT_OPTIONS`

## 2. 警戒线联动资产分类

- [x] 2.1 后端 `/api/categories/lookup` 返回增加 `警戒线`（`category.warning_line`）
- [x] 2.2 前端 `useAssetCodeAutofill`/`lookupCategoryByCode` 类型加 `警戒线`；`AssetCreatePage` 失焦联动带出 `newAsset.警戒线`；`Asset.警戒线` 类型放宽为 `number | null`
- [x] 2.3 后端资产导入：警戒线取自按 `资产编号` 反查分类的 `warning_line`（不读模板列）

## 3. 序号自动排序 + 导入模板去列

- [x] 3.1 `AssetList.vue`「序号」列改为行序号渲染 `(page-1)*pageSize + 行内序 + 1`
- [x] 3.2 后端资产导入模板（`download_template`）移除「序号」「警戒线」两列
- [x] 3.3 后端资产导入解析改为**按表头列名映射**（去序号/警戒线后抗位移）；序号自动分配（`max(序号)+1`）
- [x] 3.4 后端测试：模板无序号/警戒线列；导入序号自动分配、警戒线取自分类（并更新既有导入测试为新列序）

## 4. 验证

- [x] 4.1 后端 `pytest` 全绿（360 passed）
- [x] 4.2 前端 `vue-tsc --noEmit` 通过（exit 0）
- [ ] 4.3 本地手动验证：所属部门下拉、警戒线联动、序号随筛选变化、导入模板无序号/警戒线列
