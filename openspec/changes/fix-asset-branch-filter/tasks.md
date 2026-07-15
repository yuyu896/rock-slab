## 1. 筛选改为按分公司名称

- [x] 1.1 后端 `AssetFilterSet`/`FixedAssetFilterSet`：`branch` 过滤字段由 `分公司编号` 改为 `分公司`
- [x] 1.2 前端 `AssetList.vue`/`FixedAssetList.vue`：分公司下拉值由 `b.code` 改为 `b.name`
- [x] 1.3 后端测试：资产/固定资产按名称筛选命中（即便分公司编号为 'WRONG-CODE' 也命中）

## 2. 导入回填分公司编号 + 模板去列

- [x] 2.1 `organizations/utils.py` 新增 `get_branch_code_map()`；`import_excel` 改为按分公司名反查回填 `分公司编号`（不再读文件列）
- [x] 2.2 资产导入模板（`download_template`）去掉「分公司编号」列
- [x] 2.3 测试：导入即便文件「分公司编号」为错误值，也回填为真实 code（`test_import_derives_branch_code_ignoring_file_value`）；模板无分公司编号列

## 3. 验证

- [x] 3.1 后端 `pytest` 全绿（370 passed）
- [x] 3.2 前端 `vue-tsc --noEmit` 通过（exit 0）
- [ ] 3.3 本地手动：导入一批资产后，按分公司筛选能命中（含编号不一致的导入资产）
