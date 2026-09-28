## 1. 后端改名

- [ ] 1.1 `models.py`：`调拨日期→单据日期`、`调拨原因→事由` 字段名与 verbose_name；Meta verbose_name「调拨记录→流转单记录」
- [ ] 1.2 手写迁移 0028：两条 RenameField（禁 makemigrations 自动生成——0021 Remove+Add 教训）；本地 migrate + 行数/非空计数验证无损
- [ ] 1.3 后端引用替换（语境三分法）：models/serializers/services/views/instances/ledger——字段引用改新名；TYPE_TEMPLATES 表头、导出 headers 列标签、`_num/_cell(row,'列名')` 标签白名单不动；注释跟随改
- [ ] 1.4 收口：`grep -rn "调拨日期" backend/apps`（排除 migrations）与 `调拨原因` 同检，残留仅剩标签白名单；`manage.py check` 过

## 2. 前端改名

- [ ] 2.1 五类创建页 + 移动端 4 页：`form.调拨日期→form.单据日期`（模板标签文案不动）、payload key、`调拨原因→事由`（如有表单绑定）
- [ ] 2.2 列表/详情/台账取值：`item./doc.调拨日期→单据日期`；types/index.ts 字段定义
- [ ] 2.3 收口：`grep -rn "调拨日期" frontend/src`（排除 tests）残留仅标签/占位文案白名单；`npm run build` 过

## 3. 测试与门禁

- [ ] 3.1 前后端测试夹具与断言同步改（payload key/断言字段/模板样例行不变——列标签兼容）
- [ ] 3.2 门禁：后端 pytest 全绿（含对账）、前端 vitest 全绿、`npm run build` 通过

## 4. 收口

- [ ] 4.1 拆两 commit（chore + openspec）并 push，等用户本地手验（五类建单/详情/导入导出/移动端）后自行部署
- [ ] 4.2 部署项：0028 RenameField 随 migrate；上线抽查单据日期显示正常、导入旧模板照常、对账零差异
