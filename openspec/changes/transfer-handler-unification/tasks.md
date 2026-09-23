## 1. 后端字段重命名与服务端默认

- [x] 1.1 Transfer 模型 `采购经办人` → `经办人`（字段名与 verbose_name），生成并核对 RenameField 迁移（纯 DDL，无 DML）
- [x] 1.2 `serializers.py`：TransferSerializer 读字段与 TransferActionSerializer 写字段同步改名（:56、:143）
- [x] 1.3 `views.py` `_create_action`：创建人默认之后补经办人空值回填（`data['经办人'] = data['创建人']`），覆盖五类建单入口
- [x] 1.4 `views.py` 导出：purchase 导出列头「采购经办人」→「经办人」（:493、:501）；assign 导出补「经办人」列（:504 段）；调拨导出补「经办人」列（:551 段）；recovery 导出取值字段名同步（:549）
- [x] 1.5 `filters.py` keyword 搜索：`采购经办人__icontains` → `经办人__icontains`（:39）
- [x] 1.6 后端收口核查：`grep -rn "采购经办人" backend/apps --include="*.py"` 排除 migrations 历史后为零

## 2. 前端统一

- [x] 2.1 `types/index.ts`：采购类型 `采购经办人` key → `经办人`（:319）
- [x] 2.2 PurchaseCreate：key 与标签「采购经办人」→「经办人」（:19、:54、:84），placeholder 注明「默认创建人」
- [x] 2.3 PurchaseDetail：查看与编辑的 key/标签改「经办人」（:87、:116、:126），extra 区经办人条目移除（改由布局 meta 统一，见 2.7）
- [x] 2.4 RecoveryCreate：key 改 `经办人`、表单初始值预填当前登录人姓名（:31、:128、:189）
- [x] 2.5 RecoveryDetail：key 改 `经办人`（:45）
- [x] 2.6 AssignCreate / TransferCreate：表单新增「经办人」（预填当前登录人、可改、选填），提交 payload 带 `经办人`
- [x] 2.7 TransferDetailLayout：meta 区「创建人」旁增「经办人」（`经办人 || 创建人`），四类详情统一
- [x] 2.8 四类 List 列：「经办人」列统一渲染 `item.经办人 || item.创建人`（PurchaseList:110、RecoveryList:98、AssignList:102、TransferList:91）
- [x] 2.9 前端收口核查：`grep -rn "采购经办人" frontend/src` 排除 tests 后逐处判断归零（importTemplate.ts:108 为固定档案导出表头，非流转单据，如实保留则记录理由）

## 3. 测试与门禁

- [x] 3.1 后端测试：建单不传经办人回填创建人（含 assign/transfer 类型）；显式传入不被覆盖；导出列头与领用/调拨导出新增列
- [x] 3.2 前端测试：四类创建页预填与提交 payload；列表兜底渲染；采购详情编辑标签
- [x] 3.3 门禁：后端 pytest 全绿（含 check_ledger_consistency）、前端 vitest 全绿、`npm run build` 通过

## 4. 收口

- [x] 4.1 拆两 commit（feat + openspec）并 push，等用户本地手验（四类创建/列表/详情/导出）后自行部署
- [ ] 4.2 部署项：migrate 跑 RenameField（元数据级）；部署后抽查存量领用单列表「经办人」兜底显示创建人
