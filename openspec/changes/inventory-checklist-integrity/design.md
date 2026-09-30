## Context

`start`（inventories/views.py:86-130）：空清单预检 → `_transition`（内含事务+任务行锁）提交 in_progress → **事务外**调 `_generate_items/_generate_instance_items`（get_or_create 逐行，两方法均未用 self）。`check`（133-195）：普通 `get_object` 读 + 状态判断 + 台账盘 `InventoryItem.get_or_create` 现建项；`check_instance`（197+）同样普通读但已限 `instance_items` 清单内。盘点锁状态集 `['in_progress','pending_review']` 在 transfers 与 inventories 各自内联。台账导入确认（assets import confirm）无盘点锁检查。

## Goals / Non-Goals

**Goals:**

- 「in_progress 且清单不完整/为空」状态不可达：生成失败 → 状态与清单同回滚（保持 pending）
- 核对入口与状态机动作同一把任务行锁下串行；台账盘应盘范围=开始时刻快照（与实例盘同口径）
- 实盘数量域=非负整数（API 与 Excel 导入两路一致拒绝）
- 「盘点期间台账冻结」三路对称：创建 / 审批 / 导入确认

**Non-Goals:**

- 不改清单生成条件与 expected_qty 口径（总量三列合计，inventory-scope-rework 语义）
- 不补 start 时「存量待审批单」的提示（审批侧已拦，UX 另案）
- 不处理存量历史 in_progress 任务的清单修复（部署时如有此态任务，运维取消重开即可；新代码不会再产生）
- 不动 repeat_rule/missed_rule 语义

## Decisions

**1. 生成函数抽为模块级 `generate_task_checklist(task)`，start 的 `before_save` 内调用。**
两生成器本就不依赖 self；模块化后 start 在 `_transition` 事务内（before_save 钩子）调用即可获得原子性，测试造数也能直接复用。幂等性保留（get_or_create）。

**2. check/check_instance 重构：`transaction.atomic` + `InventoryTask.objects.select_for_update()` 重取任务 + 锁内复查 status，台账盘改查 `InventoryItem.objects.filter(task, stock)`，缺行 404。**
任务行锁是串行化锚点（submit/approve/cancel 的 `_transition` 同锁），check 持同锁即消除「核对中单据被提交/审批」竞态；item 级锁不再需要（任务锁已覆盖并发核对同项）。404 文案注明「清单于开始盘点时生成」，指引用户重开任务而非迷惑。

**3. 数量校验：serializer `min_value=0`（API 路）+ 导入路显式整数解析。**
openpyxl 数值格常给 float：整数 float（5.0）接受（`float.is_integer()` 收敛为 int），非整数（2.9）与不可解析值进 errors（「实盘数量必须为整数」）。不再 `int(float())` 静默截断。

**4. 盘点锁共享常量 `INVENTORY_LOCKED_STATUSES` 放 inventories/models.py，三处引用。**
transfers `_check_inventory_lock` 的过滤、inventories start 的同分公司复查、assets 导入确认的新检查，统一口径防漂移。导入确认的报错聚合全部锁定分公司名（一次说清，不逐行报）。

**5. 存量测试造数对齐真实语义。**
凡 ORM 直造 in_progress 任务后调 check 的用例，补 `generate_task_checklist(task)`（或手工建 InventoryItem），使造数等价于真实 start——这本来就是这些用例的前提假设。

## Risks / Trade-offs

- [清单外台账行（开始后新出现的行）无法核对] → 开始后建单/审批/导入三路已锁，新行不应出现；若真出现说明有未锁路径，404 暴露问题优于静默盘入
- [存量历史 in_progress 任务清单不全，check 会 404] → 该状态本就锁死分公司（旧缺陷产物），取消重开即恢复；无迁移必要
- [check 加锁增加一次行锁获取] → 盘点核对频度低，任务粒度锁竞争面小

## Migration Plan

纯代码，无迁移。部署即生效；回滚 revert。上线验证：盘点期间对目标分公司做台账导入确认应得 400 INVENTORY_LOCKED；负数/小数实盘应被拒。
