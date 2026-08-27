## 1. 新建/创建页撑满（修订 1.1）

- [x] 1.1 `TransferCreateLayout.vue` 移除 `.create-page` 960px 限宽与居中，`.form-grid` 超宽屏限列宽（minmax(0, 640px)）
- [x] 1.2 `InventoryTaskCreate.vue` 移除 640px 限宽，字段改两列栅格（任务名称跨列），观感与流转新建页一致

## 2. 采购行金额自动计算（修订 2.1）

- [x] 2.1 前端 `TransferLinesEditor.vue`：数量/单价/金额 change 联动——金额为空且单价非空时补算（空字符串归一 null），手填不覆盖
- [x] 2.2 后端 `validate_line_items_instances`：purchase 行有单价无金额补算（Decimal × 数量），三路径（创建/编辑/导入）共用生效
- [x] 2.3 后端测试：表单创建补算、手填优先、无单价不补算、导入路径同口径

## 3. 领用行使用人/部门必填（修订 2.2）

- [x] 3.1 前端 `TransferLinesEditor.vue`：assign 行使用人/部门必填（不分管理方式），部门下拉占位随分公司选择状态切换（"请先选择所属分公司"/"请选择部门"），表头加必填标记
- [x] 3.2 前端提交校验与提示文案更新（AssignCreate 提交警告含使用人/部门引导）
- [x] 3.3 后端 `validate_line_items_instances`：assign 全部行强制 使用人 非空 + department 非空，错误带行号×品目定位
- [x] 3.4 领用导入模板加"使用人"列（分公司、日期、资产编号、领用物品、领用数量、使用人、领用部门、用途、备注），导入解析映射行使用人；领用部门列按（分公司, 部门名）解析行级 Department 外键（单头文本照写），解析失败/缺失逐行报错
- [x] 3.5 后端测试：领用缺使用人/部门 400（表单与导入两路）、部门解析失败报错、既有合法领用用例补字段后通过

## 4. 回收创建页在用预检与报错业务化（修订 1.3）

- [x] 4.1 后端 `AssetStockFilterSet` 增 `asset_code`（item__asset_code 精确）过滤；前端 `api/assets.ts` getAssetStocks 透传参数
- [x] 4.2 前端 `TransferLinesEditor.vue`：type=recovery 时按（调出分公司 × 品目）拉在用数量缓存，行内展示"在用 N"，数量超出即时标红
- [x] 4.3 前端 `validate()`：同品目多行合并在用预检拦截（未知行放行，终检在后端）
- [x] 4.4 后端 `ledger.apply_document`：recovery 分支 LEDGER_INSUFFICIENT 报错改业务语言（"回收只能回收『在用』中的资产：当前在用 N…"），保留行号×品目定位；其他单据报错格式不变
- [x] 4.5 后端测试：在用不足回收审批报错文案、在用充足通过、归还等他类报错格式不回归

## 5. 验证与收尾

- [x] 5.1 后端 `pytest` 全绿（含 `python manage.py check_ledger_consistency` 相关用例）
- [x] 5.2 前端 `npm run build`（类型门禁）+ `npm run test` 全绿
- [x] 5.3 feat + openspec 两个 commit → push → 归档 change，v2-revision-draft.md 第 1 案状态改 ✅
