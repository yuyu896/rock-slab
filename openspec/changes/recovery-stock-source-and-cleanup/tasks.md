## 1. 后端双源与校验

- [x] 1.1 `ledger.py` `_plan` 回收分支：按行派生扣列——实例行读实例实际状态（在用/在库）扣对应列；数量行固定扣在库；restock 分支维持现状（仅实例在用）
- [x] 1.2 `services.py` 预检分流：dispose 实例状态放宽（在库/在用均可，品目/分公司校验照旧）；dispose 数量行校验在库充足；restock 拒绝数量品（提示无重新入库概念）与在库实例（提示无需回库）
- [x] 1.3 `instances.py` `expected_state`/`check_line_instances`：dispose 允许双态；restock 维持在用
- [x] 1.4 `serializers.py` validate 补处置必填：dispose→处置方式必填；出售→处置金额必填且 ≥0
- [x] 1.5 回收台账：`'经办人': t.经办人 or t.创建人`（views.py:606）；响应附 `disposal_income`（出售单金额加总，当前筛选口径），导出同步
- [x] 1.6 后端收口核查：处置校验、扣列派生、台账口径三处 grep 确认无遗漏引用

## 2. 前端表单与列表

- [x] 2.1 `RecoveryCreate`：下线回收分类、出库日期表单项；提交 payload 不再携带（存量编辑草稿透传不回写）
- [x] 2.2 `TransferLinesEditor` 回收模式按去向分流：dispose——数量行品目点选按在库数量收口（新增在库数量缓存）、实例行 InstancePicker 状态筛放宽为在库+在用；restock——维持现状（仅实例品目、在用实例）；去向切换行失效重校验
- [x] 2.3 `RecoveryList`：入库日期→回收日期；回收分类列、出库日期列退役；`RecoveryDetail` 去向三态修复（dispose=直接处置 / restock=重新入库 / 存量 recycle_bin=入回收库）、回收分类/出库日期展示下线
- [x] 2.4 `RecoveryLedger`：页顶处置收入合计卡；导出列同步（回收分类/出库日期若在列则退役）
- [x] 2.5 `types/index.ts` 同步（回收分类/出库日期可写属性删除；台账行类型补合计）

## 3. 测试与门禁

- [x] 3.1 后端测试：数量品在库处置（台账/进回收台账）；在库实例处置退役；在用处置回归；restock 三拒绝（数量品/在库实例/消耗品既有）；数量行在库不足拒绝；处置必填双校验 400；台账经办人同源与收入合计
- [x] 3.2 前端测试：建单页去向分流取数（dispose 在库列/双态实例；restock 现状）；去向三态展示；合计卡渲染
- [x] 3.3 门禁：后端 pytest 全绿（含对账）、前端 vitest 全绿、`npm run build` 通过

## 4. 收口

- [x] 4.1 拆两 commit（feat + openspec）并 push，等用户本地手验（重点：办公桌在库报废全链路）后自行部署
- [ ] 4.2 部署项：无迁移；上线后抽查——存量回收单列表回收日期/无分类出库列；台账经办人同源；对账零差异
