## 1. 模型与迁移

- [x] 1.1 `LedgerAdjustment` 加字段：`单据编号`（CharField 32，unique，null/blank，db_index）、`source_task`（FK→inventories.InventoryTask，null/blank，SET_NULL，related_name='adjustments'，verbose_name=来源盘点任务）
- [x] 1.2 `transfers/services.py` 的 `DOC_NUMBER_PREFIXES` 加 `'adjust': 'TZ'`
- [x] 1.3 迁移一：AddField（两列均 nullable，旧代码兼容）
- [x] 1.4 迁移二：纯 Python 回填存量编号（created_at 升序逐行 `generate_document_number`，按 编号 IS NULL 幂等可重跑，禁数据库聚合）

## 2. 服务层

- [x] 2.1 `ledger.apply_adjustment` 加 `source_task=None` 参数并在创建时落来源；函数内延迟导入 `generate_document_number('adjust', now)` 生成编号写入
- [x] 2.2 新建 `inventories/services.py`：`generate_variance_adjustments(task, approver)`——枚举 `result__in=['surplus','missing']` 且 `actual_qty` 非空的项，逐项调 `apply_adjustment`（目标列=在库数量，变动量=actual−expected，经办人=approver，source_task=task，事由=`盘点差异「{task.name}」：在库 {expected} → {actual}（盘盈/盘亏 N）`）；无差异返回空列表
- [x] 2.3 确认嵌套事务语义：钩子外层事务 + apply_adjustment 内层 atomic（保存点），任一行 LEDGER_INSUFFICIENT 整体回滚且错误定位分公司×品目

## 3. 视图与序列化

- [x] 3.1 `inventories/views.py` approve 的 `_adjust` 钩子改调 `generate_variance_adjustments(t, request.user)`，保留 completed_at 写入；错误经既有 `_transition` 回滚路径返回 400
- [x] 3.2 `LedgerAdjustmentSerializer` 加 `单据编号` 与来源任务展示（任务 id+名称）；列表筛选参数：分公司、品目编号、日期区间
- [x] 3.3 `LedgerAdjustmentViewSet.create` 补 `audit_create` 审计留痕（resource_type=LedgerAdjustment）
- [x] 3.4 盘点 completed 通知的 extra_data 附生成调整单数（盘盈/盘亏分计），通知契约不变

## 4. 前端

- [x] 4.1 `api/assets.ts` 加 `listAdjustments`（分页+筛选）与 `createAdjustment`；`types/index.ts` 补调整单类型（含编号/来源任务）
- [x] 4.2 台账主视图行内"调整"按钮（持 `adjust_ledger` 可见）+ 开单弹窗（分公司/品目预填只读，目标列/变动量/事由），成功后就地刷新行数量并提示编号，失败展示后端定位信息
- [x] 4.3 台账主视图页面级"调整记录"弹窗：Excel 式朴素表格（编号/时间/分公司/品目/目标列/变动量/事由/经办人/来源），分公司/编号/日期筛选 + 分页
- [x] 4.4 盘点审批通过前确认弹窗：差异预览（编号、在库 应盘→实盘、±N）+ 明示将生成调整单数；无差异明示零单；取消不审批
- [x] 4.5 盘点报告弹窗加已生成调整单汇总（总数 + 盘盈/盘亏分计）

## 5. 测试与验收

- [x] 5.1 重写 `tests/test_ledger_contract.py` 既有「审批后台账不变」断言（:250-268）为「审批后按差异修正」契约
- [x] 5.2 新增盘点差异开单用例：盘亏/盘盈各一、事由与经办人与来源正确、台账同步修正
- [x] 5.3 新增边界用例：漏盘 zero 生成盘亏单 / keep 不生成、无差异零单、不足整笔回滚（任务留 pending_review、台账与调整单零残留）
- [x] 5.4 新增编号用例：并发（同日两单不同号）、存量回填迁移幂等重跑
- [x] 5.5 新增手动开单审计断言（audit log 落一行）与序列化来源字段断言
- [x] 5.6 前端 vitest：调整弹窗提交与失败展示、审批预览弹窗差异计数
- [x] 5.7 全量验收：后端 pytest 全绿（含架构测试与 check_ledger_consistency）、前端 vitest 全绿、`npm run build` 通过
