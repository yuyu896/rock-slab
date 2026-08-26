## Context

2026-08-25 五路契约审计（对照总设计书 asset-model-v2.md 与全部 asset-v2 提案）人工复核确认 4 条高危，全部属于「防线缺口」而非主干契约违背：主干（五单联动、唯一写入口、组织树、权限同源）已核无恙。缺口集中在两类——P3/导入新增的写路径没有跟上 `validate_branches_in_scope` 的既有防线（该函数全后端仅 3 处调用，全在表单路径），以及「数量品目 × 实例」的双向污染路径（自动生成侧无守卫、管理方式切换侧无守卫）。

现有关键事实：
- `core/permissions.py:54 validate_branches_in_scope(user, *branch_values)`：admin 豁免、非 None 值逐一求差集，越界抛 ValidationError。流转创建（transfers/views.py:132）、流转编辑（:321）、盘点创建（inventories/views.py:45）已在用。
- 操作码（OperationGrant）是全局的，无范围维度；范围校验责任全在写入口。
- 导入路径已有行级错误收集语义：编号不在字典 → 该行进 `errors`，合法行继续。
- `generate_instances`（assets/services/instances.py:109）无管理方式判断；`check_line_instances` 只拦「用户携带实例」，拦不住自动生成。
- 盘点 `InventoryTaskSerializer` 的 `branch`/`status` 均可写，视图无 update 覆写；`_transition` 状态机不走 serializer（锁内直接改），故字段收紧不影响状态机动作。

## Goals / Non-Goals

**Goals:**
- 持全局操作码但范围受限的用户，无法经调整单、台账导入、流转导入、盘点任务对范围外分公司做任何写操作（含预览阶段的越权读）。
- 盘点任务的分公司与状态只能经既有创建/状态机动作改变，PATCH 不可绕过。
- 采购数量管理品目不再生成实例档案；品目管理方式在有存量时不可切换。
- 审计指出的测试盲区补上（数量品目采购断言实例数为 0）。

**Non-Goals:**
- 处置单（用户拍板不需要：处置决策在回收时刻作出，回收单二选一已覆盖）。
- 盘点 start 无锁竞态与 recount 绕过唯一活动盘点的并发问题（审计中危 #9 群，另行提案）。
- 架构测试模式加固、报表时间范围、导出部门列等 P1/P2 项（另行提案）。
- 盘点 `branch` 的数据库层 NOT NULL 化（避免迁移与存量数据处理，收紧在序列化层）。

## Decisions

**D1 范围校验统一复用 `validate_branches_in_scope`，不另写判定。**
同源保证 admin 豁免与范围口径与表单路径完全一致；避免第二套范围算法（权限矩阵漂移的教训）。单对象入口（调整单 create、盘点 create）沿用「越界 400 不落库」；批量导入入口（台账/流转）按既有行级语义处理——越权行进 `errors`（提示「分公司 X 不在你的授权范围」），不进 diffs、不可被 confirm，合法行照常。备选「整文件 400 拒绝」被否：与「编号不在字典整行拒绝、合法行继续」的既有导入语义不一致，且一个越权行就废掉整份文件体验更差。

**D2 盘点加固在序列化层：`branch` 创建必填 + `branch`/`status` 永久只读。**
`read_only_fields` 使 PATCH 静默忽略这两个字段（DRF 默认行为），无需覆写 update；状态机动作（start/submit/approve/reject/recount）经 `_transition` 锁内直改，不受影响。备选「模型 null=False + 迁移」被否：验收期引入迁移收益低、还需处理假想的存量 branchless 任务；生产按对账与验收手册走的是全公司/单分公司盘点，当前无 branchless 任务（测试中固定该假设）。

**D3 `generate_instances` 守卫放在函数内部，不在调用侧。**
`if line.item.management_type != 'instance': return []`——守卫贴近生成逻辑，未来任何新调用方自动受保护（与 `check_line_instances` 的守卫位置对称）。数量品目采购行静默跳过生成（单据本身合法，台账动作照常），无需报错。

**D4 管理方式切换守卫在 `CategorySerializer.update`，判定条件 = 挂实例 或 台账任一列非零。**
`FixedAsset.objects.filter(item=…).exists()` 或 `AssetStock.objects.filter(Q(在库数量__gt=0)|Q(在用数量__gt=0)|Q(回收库数量__gt=0), item=…).exists()` 时拒绝 `management_type` 变更，400 提示存量状况与解锁路径（存量清零后可切）。备选「切换时自动对齐（退役实例/补生成实例）」被否：隐式改账违背单据纪律，切换是管理决策，应显式清场后进行。序列化器输出派生只读布尔 `management_locked`（同一判定函数），编辑弹窗据此禁用下拉并提示原因——展示派生字段，不构成第二事实源。

**D5 前端配套最小化。**
盘点创建表单分公司必选（后端 400 兜底，前端校验先行）；品目编辑弹窗消费 `management_locked`。其余（调整单/导入）前端无需改——越权行进 errors 的既有展示链路已覆盖。

## Risks / Trade-offs

- [存在其他盘点创建调用方传空 branch，升级后收到 400] → tasks 中 grep 全部创建入口（PC/移动端）核对；验收手册盘点章节同步必选语义。
- [生产存在历史 branchless 盘点任务，branch 只读后无法修正] → 验收期盘点任务可删重建；如确有存量，走管理命令一次性清理（本提案不含，出现再议）。
- [PATCH 静默忽略 branch/status，前端若依赖 PATCH 改这些字段会静默失效] → grep 前端盘点 PATCH 调用确认无使用；测试固定「PATCH 含 status 不生效」。
- [数量品目采购不产实例后，若有人误以为实例丢失] → 契约测试断言双口径：数量品目实例数 0、台账在库 +N。

## Migration Plan

纯代码与测试改动，无数据库迁移、无数据回填。部署走常规 `bash deploy.sh`（pytest + 对账闸门照常）。回滚 = revert 对应 commit 再部署；防线收紧不产生需要回滚的数据形态。

## Open Questions

（无——处置单已拍板不做；其余范围问题审计阶段均已确认。）
