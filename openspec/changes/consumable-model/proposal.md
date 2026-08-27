## Why

2026-08-27 补修宪（设计书 #2/5.1/5.2/5.4，拆案第 8 案）：管理方式此前只有数量/实例两档，低值易耗品（B 类）作为数量管理品目走"领用进在用"语义——但纸巾、纸杯这些东西领出即消耗，不存在"收回再分配"，挂"在用"是假账（生产期初单里大量 B 类在用余额即此产物），也无法回收。定案增加第三档「**消耗品**」：领用即耗用发放（在库−N、总量降，记领用人签字/部门，不进在用、无回收）。本案为拆案计划最后一案。

## What Changes

- **管理方式三档**：`Category.management_type` 增 `consumable`（消耗品）档；前端字典表单/各处展示同步三档。
- **领用耗用发放联动**：`_line_plan` 领用行按品目管理方式分流——数量/实例品目维持现状（来源列−N、在用+N）；**消耗品行 = 在库−N（总量随之降），不进在用**。对账命令与 `_line_plan` 同源，自动跟随。
- **消耗品单据约束（预检层拦截）**：回收单、归还单拒消耗品行（"消耗品无回收/无可还，领出时已耗用出账"）；领用来源=回收库的消耗品行拒（消耗品无回收库）。调拨、采购对消耗品正常可用（在库两向）。
- **存量 B 类迁移命令**：`migrate_consumables`（默认 dry-run 预览清单）——低值易耗品类 × 数量管理 × 在用=0 且回收库=0 的品目 `--apply` 直改字典属性；在用或回收库非零的列出并警示（先调整归零/清空再迁）；实例管理的 B 类列出供人工决断（不改）。迁移不改任何台账数量（铁律 2），对账前后一致（在用=0 时新旧矩阵重放等价）。
- **盘点口径**：消耗品天然只参与台账盘（在库列），不进在用/实例盘（无实例、不进在用），无需额外改动。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `document-ledger-sync`: 「五单台账联动矩阵」领用行按品目管理方式分流（消耗品 = 在库−N 总量降，不进在用）；新增「消耗品单据约束」requirement（回收/归还/回收库来源拒绝消耗品行，预检层拦截）。
- `item-dictionary`: 「品目字典数据模型」管理方式三档（quantity/instance/consumable）；新增「存量消耗品迁移命令」requirement（预览清单 + 只迁在用/回收库双零 + 命令直改字典属性绕过页面切换锁）。

## Impact

- **后端**：`apps/categories/models.py`（choices 三档 + migration 纯 DDL）、`apps/assets/services/ledger.py`（assign 分流）、`apps/transfers/services.py`（预检三处拦截 + 文案兼容三档）、新增 `apps/categories/management/commands/migrate_consumables.py`。
- **前端**：`constants`（管理方式标签映射）、`types`（'consumable'）、`CategoryCreate.vue`（三档下拉+说明）、`Category.vue`/`AssetSummary.vue`/`ItemPicker.vue`/移动端两处（二元判断改标签映射）、`AssignCreate.vue`/`TransferLinesEditor.vue`（消耗品行提示）。
- **测试**：联动矩阵（消耗品领用在库−N 总量降在用不动）、三处预检拒绝、采购/调拨正常、命令 dry-run/apply/跳过逻辑、全量回归。
- **兼容**：既有 quantity/instance 品目行为零变化；对账矩阵同源跟随；生产存量迁移走命令（部署后手动 dry-run→apply）。
