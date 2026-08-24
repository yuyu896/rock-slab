## Why

P3 验收标准（设计书第九节）：盘点差异自动生成调整单。现状盘点为记录模式——审批通过后差异只留在盘点结果里，台账与实际"讲的不是同一件事"，修数全靠持 `adjust_ledger` 者看报告后手工开单，漏开、错开无守护。同时调整单自身是半成品：无单据编号、无来源追溯、无审计留痕、前端没有任何查看/开单入口。

## What Changes

- **盘点差异自动生成调整单**：盘点审批通过时（`_transition` 锁内事务内），逐差异行（盘盈/盘亏）经唯一写入口 `apply_adjustment` 开调整单——目标列=在库数量（盘点只盘在库列），变动量=实盘−应盘，事由含任务名与前后数量，经办人=审批人；台账随审批同步修正。任一行致负数则整笔审批失败回滚（任务留在 pending_review），差异必须暴露不允许吞掉。
- **调整单模型补全**：加单据编号（复用 `DocumentSequence` 发号，前缀 TZ，锁行自增防并发重号）与来源盘点任务 FK（nullable，手动开单为空）；存量行纯 Python 回填编号（禁数据库特定聚合）。
- **调整单落定为创建即生效**：不设审批流（docstring "P3 按需补充"就此结案——盘点路径的审批已由盘点任务承担，手动路径与导入路径同级、靠审计与权限约束）；手动开单 API 补审计留痕。
- **前端补调整单整块 UI**：台账主视图行内"调整"按钮（弹窗开单，预填分公司×品目）+ 页面级"调整记录"列表（Excel 式朴素表格，含编号/来源任务）；盘点审批前确认弹窗预览将生成的差异调整，报告页展示已生成调整单数。

## Capabilities

### New Capabilities
- `ledger-adjustment-ui`: 调整单前端整块——台账行内开单入口、调整记录列表、盘点审批差异预览与结果反馈（Excel 式朴素表格风格）。

### Modified Capabilities
- `inventory-item-basis`: 「盘点差异为记录模式」修订为「盘点差异自动生成调整单」——审批通过即开单修台账，不足整笔回滚；漏盘归零规则产生的盘亏同样开单。
- `document-ledger-sync`: 「调整单」需求扩展——新增单据编号与来源任务字段，明确创建即生效（不设审批流）、审计留痕与三条创建路径（手动/导入/盘点差异）。

## Impact

- 后端：`apps/assets/models.py`（LedgerAdjustment 加字段 + 迁移 + 存量回填）、`apps/assets/services/ledger.py`（apply_adjustment 发编号/记来源）、`apps/inventories/views.py`（approve 的 `_adjust` 钩子接差异开单）、`apps/assets/views.py`（手动开单补 audit）、`apps/transfers/services.py`（DOC_NUMBER_PREFIXES 加 adjust）。
- 前端：`views/assets/AssetSummary.vue`（行内调整 + 调整记录）、`views/Inventory.vue`（审批确认预览）、`views/inventory/InventoryReport.vue`（生成结果展示）、`api/assets.ts`。
- 测试：`tests/test_ledger_contract.py` 现有「审批后台账不变」断言（:250-268）随契约修订重写；新增差异开单/回滚/幂等用例；架构测试（唯一写入口）不放松。
- 不动：对账命令口径（调整单本就在流水内）、通知机制（completed 通知 extra_data 附调整数，属增强不改契约）、权限操作码（沿用 `adjust_ledger`）。
