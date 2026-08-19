## 1. 资产列表分公司筛选

- [x] 1.1 `AssetList.vue` 分公司下拉 `value` 由 `b.name` 改为 `b.code`（label 仍为 `b.name`）
- [x] 1.2 后端测试：资产列表按 `branch=<编号>` 筛选命中

## 2. 流转列表分公司筛选

- [x] 2.1 `composables/useTransferList.ts` 分公司下拉 `value` 由 `b.id` 改为 `b.name`
- [x] 2.2 后端 `apps/transfers/views.py` `_create_action` 创建流转时回填：`调出分公司 = from_branch.name`、`调入分公司 = to_branch.name`（外键存在且名称为空时）
- [x] 2.3 后端测试：流转按 `fromBranch=<名称>` 筛选命中；表单创建后 `调出分公司`/`调入分公司` 回填为名称非空

## 3. 验证

- [x] 3.1 后端 `pytest` 全绿（357 passed，含固定资产按编号筛选回归用例）
- [x] 3.2 前端 `vue-tsc --noEmit` 通过（exit 0）
- [ ] 3.3 本地手动验证：资产列表、流转列表分公司筛选均能命中；固定资产/盘点不受影响
