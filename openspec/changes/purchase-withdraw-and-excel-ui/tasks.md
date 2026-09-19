# 任务：采购入库单自助撤回 + Excel 表格改版

## 1. 后端撤回与草稿编辑

- [x] 1.1 `views.py` 新增 `withdraw` action：镜像 submit/resubmit 模式（permission + `_assert_transfer_operable` + `@audit_log(action='withdraw')`），守卫「待审批 + 创建人==当前用户姓名」，通过后置 `草稿`
- [x] 1.2 `update` 守卫扩展：`仅已驳回` → `已驳回或草稿`
- [x] 1.3 后端测试：创建人撤回成功；非创建人拒绝；非待审批（草稿/已通过/已驳回/已入库）拒绝；撤回后编辑再 submit 全链路；台账无变动断言

## 2. 前端撤回入口

- [x] 2.1 `api/transfers.ts` 新增 `withdrawPurchase(id)`（实现为通用 `withdrawTransfer`）
- [x] 2.2 `PurchaseDetail.vue` 操作区加「撤回」按钮：`待审批 && doc.创建人 === 当前用户姓名` 才渲染；确认弹窗防误触；成功后刷新为草稿态（露出编辑/提交）

## 3. Excel 表格改版

- [x] 3.1 `PurchaseCreate.vue`：核实已达标（表头本无供应商输入、行编辑器已有供应商列），零改动
- [x] 3.2 `PurchaseDetail.vue`：明细表增供应商列（TransferLinesTable，行级空回退表头值），表头信息区移除供应商字段，编辑表单移除表头供应商输入；另补草稿态「修改/提交审批」入口，表头信息区移除供应商字段；行级空时显示 `doc.供应商` 兜底；编辑表单同步调整

## 4. 验证收口

- [x] 4.1 后端 pytest 全量（768 过/1 跳/6 xf）+ 前端 vitest 全量（144 绿）+ `npm run build` 类型门禁通过
- [ ] 4.2 手验收口：创建一张待审批采购单 → 创建人撤回 → 编辑改供应商/数量 → 重新提交 → 审批入库；他人视角无撤回按钮；存量老单详情供应商正常显示
