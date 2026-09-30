## Why

安全审计动态复现的四个盘点完整性缺口：① **启动非原子**——`start` 经 `_transition` 提交 in_progress 后才在事务外生成清单，生成失败则任务停留在 in_progress 且清单 0 条，空清单任务锁死全分公司建单且无自愈；② **check 无行锁且台账盘绕清单**——与 submit/approve 的 `_transition` 行锁存在竞态，且台账盘 `get_or_create` 现建清单项，绕过 start 时的快照应盘范围（实例盘已限清单内，台账盘未对齐）；③ **数量允许负数**——`CheckItemSerializer.qty` 无 `min_value=0`，负数实盘入库还判成 missing；④ **Excel 导入小数静默截断**——`int(float())` 把 2.9 截成 2 无提示。另有同族不变量缺口：**台账导入确认不查盘点锁**——创建/审批两路已锁（后者昨日修复），独缺导入确认一路，盘点期间导入照改台账破坏快照。

## What Changes

- `start` 的清单生成收进 `_transition` 的同一事务（生成函数抽为模块级 `generate_task_checklist(task)`）：失败整体回滚、任务保持 pending，「in_progress 空清单锁死分公司」状态不再可达
- `check` / `check_instance` 加任务行锁 + 锁内状态复查；台账盘核对限清单内（不在清单 404，对齐实例盘口径）
- `CheckItemSerializer.qty` 加 `min_value=0`；盘点结果 Excel 导入的小数实盘数量改为明确报错（整数 float 如 5.0 仍接受）
- 台账导入确认前查目标分公司盘点锁：任一锁定 → 400 `INVENTORY_LOCKED`（聚合分公司名），与创建/审批同口径；锁定状态集（in_progress/pending_review）抽为 `inventories/models.INVENTORY_LOCKED_STATUSES` 共享，transfers 与 inventories 内部复查统一引用
- 存量测试中「ORM 直造 in_progress 任务即调 check」的造数补清单生成（对齐真实 start 语义）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `inventory-state-machine-concurrency`: 新增「启动与清单生成原子一致、核对入口行锁且限清单、实盘数量非负整数」要求
- `inventory-concurrency-control`: 新增「盘点锁定期间台账导入确认必须被拒」要求（补齐创建/审批/导入三路对称）

## Impact

- `backend/apps/inventories/views.py`：`generate_task_checklist` 模块函数、start 事务内生成、check/check_instance 行锁+限清单、导入小数报错
- `backend/apps/inventories/serializers.py`：qty 非负
- `backend/apps/inventories/models.py`：`INVENTORY_LOCKED_STATUSES` 共享常量
- `backend/apps/assets/views.py`：导入确认前盘点锁检查
- `backend/apps/transfers/views.py`：锁状态集改引共享常量（无行为变化）
- `backend/tests/`：新增完整性用例 + 存量 check 造数补清单
- 行为变化：负数实盘/小数导入从静默接受/截断变 400/报错行；清单外台账行 check 从现建变 404；盘点期间导入确认变 400
