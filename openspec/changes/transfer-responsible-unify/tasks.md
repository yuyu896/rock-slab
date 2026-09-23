## 1. 后端字段退役与导入兜底

- [x] 1.1 迁移 0022（数据迁移，纯 DML）：调拨单 `经办人=''` 且 `调出负责人` 非空 → 逐单把调出负责人值写入经办人（纯 Python 遍历）
- [x] 1.2 迁移 0023（结构迁移，纯 DDL，depends_on 0022）：`RemoveField(Transfer, '调出负责人')`；本地 migrate 验证存量值合并无损
- [x] 1.3 `models.py` 删字段定义；`serializers.py` 删读写两处（:54 读列表、:136 写字段）
- [x] 1.4 `views.py` 导出：调拨导出头删「调出负责人」列及取值（:558、:566）
- [x] 1.5 `views.py` TYPE_TEMPLATES transfer 表头删「调出负责人」（:82）；导入解析删 `_cell(row, '调出负责人')`、header 补 `'经办人': creator`（:906 段，对齐 :838 采购模式）
- [x] 1.6 后端收口：`grep -rn "调出负责人" backend/apps --include="*.py"` 排除 migrations 历史后为零

## 2. 前端表单与模板

- [ ] 2.1 `TransferCreate.vue`：删「调出负责人」输入；「调入负责人」改纯下拉——watch toBranch：清空已选值 + `getUsers({ branch: toBranch })` 拉员工刷新选项；未选分公司时 disabled
- [ ] 2.2 `TransferDetail.vue`：extra 区删「调出负责人」展示（:69）
- [ ] 2.3 `importTemplate.ts`：TRANSFER_HEADERS 删「调出负责人」（:20）
- [ ] 2.4 前端收口：`grep -rn "调出负责人" frontend/src` 排除 tests 后为零

## 3. 测试与门禁

- [x] 3.1 后端测试：迁移合并（空经办人取调出负责人/已有值不覆盖）；调拨导入经办人=操作人、模板 12 列表头；导出无调出负责人列
- [x] 3.2 前端测试：选调入分公司后下拉出员工选项、切换清空、未选禁用；提交 payload 带姓名快照
- [x] 3.3 门禁：后端 pytest 全绿（含对账）、前端 vitest 全绿、`npm run build` 通过

## 4. 收口

- [x] 4.1 拆两 commit（feat + openspec）并 push，等用户本地手验后自行部署
- [ ] 4.2 部署项：migrate 0022（数据合并）→ 0023（删列）顺序执行；部署后抽查存量调拨单经办人=原调出负责人、创建页无该字段、导出无该列
