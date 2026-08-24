# 提案：实例层接入与领用绑实例（资产模型 V2 · P2 第二刀）

## Why

总设计书（docs/design/asset-model-v2.md）5.3：贵重物品必须"一物一档"，实例管理品目的领用必须绑定具体实例。现状 FixedAsset 还是 V2 之前的旧模型——状态枚举（在库/在用/空闲）与设计书状态机（在库/在用/回收库/退役）不符、品目信息整组手抄存储（违反铁律 1）、`count()` 生成内部编号（设计书点名的并发竞态）、与明细行无结构化关联（回收靠文本内部编号物理删除实例，P1 过渡行为）。同时决策 #10 的"领用单增加库存来源（新品库/回收库）"尚未落地，而"从回收库挑实例"依赖它。本刀是明细行化（第一刀）之后的第二刀，为第三刀（Asset 退役 + 导航合并）扫清实例档案这一最后依赖。

## What Changes

- **FixedAsset 重塑为四态实例档案**：状态机 在库→在用→回收库→退役（退役为终态，档案永久保留）；`item` 外键（→品目字典，PROTECT）取代手抄 资产编号/名称/类目/规格 等文本列；新增出生明细行外键（供应商/单价/采购日期经出生采购行派生，决策 #8）；内部编号 `{品目编号}-{序号}` 改锁行计数器生成（`InstanceSequence`，杜绝 count() 竞态）；序列号可空 = 待补录，渐进录入
- **明细行 × 实例结构化关联**：新增行-实例关联（`TransferLine.instances` 多对多）；实例管理品目的领用/归还/调拨/回收行 MUST 携带与数量等长的实例引用（uuid 数组），数量管理品目与采购行 MUST NOT 携带（采购行生效时自动生成实例）
- **领用库存来源（决策 #10）**：领用单单头新增 `领用来源`（新品库/回收库，默认新品库），台账联动按来源扣 在库 或 回收库 列
- **五单实例联动矩阵（与台账数量同事务）**：采购生成实例（在库）→ 领用绑使用人转在用（按来源从在库或回收库挑）→ 归还清使用人回在库 → 调拨实例分公司跟随 → 回收入回收库/直接处置转退役；实例充足性（状态/分公司/品目匹配）在行锁事务内终检，不足整单回滚
- **回收物理删除退役**：删除 P1 过渡行为（按行文本内部编号物理删 FixedAsset）；`TransferLine.固定资产内部编号` 文本列删除（实例引用取代）
- **BREAKING** FixedAsset 写接口冻结：手动创建/编辑/删除/批量删除/Excel 导入全部下线（实例出生=采购单，存量=迁移，序号/备注补录除外）；新增序列号补录端点（`manage_instances` 权限）
- **对账执法扩展**：`check_ledger_consistency` 新增实例不变量——实例管理品目 × 分公司，各状态实例计数 == 台账对应列；迁移末尾对存量差异生成期初调整单（is_initial）一次性对齐
- **前端**：固定资产列表页重做（联字典新列、待补录标识、补录弹窗、生平视图 = 出生信息 + 关联单据行）；领用创建页加库存来源与实例点选；归还/调拨/回收创建页加实例点选；单据详情明细表加实例列；固定资产手动创建页下线

不在本刀范围（后续提案）：Asset 退役与导航合并（P2 第三刀）、独立处置单与盘点差异联动调整单（P3）、实例期初批量导入（如需，P3 另立提案）。

## Capabilities

### New Capabilities
- `document-instance-binding`: 单据 × 实例绑定与联动——明细行实例引用的输入校验（品目管理方式 × 单据类型矩阵）、领用库存来源、五单生效时实例状态迁移与充足性行锁校验

### Modified Capabilities
- `fixed-asset-instance`: 模型整体重塑（四态状态机、item 外键、出生行追溯、锁行编号、去手抄列）；API 从手动 CRUD 改为冻结只读 + 序列号补录 + 生平查询；旧"数量同步 Asset"requirements 废止
- `transfer-line-items`: 明细行输入/输出形状扩展（instances uuid 数组、实例列回显）；回收行 固定资产内部编号 文本列删除
- `document-ledger-sync`: 领用矩阵按库存来源扣列（在库 或 回收库）；实例状态迁移与台账数量变动同事务；回收不再物理删除实例
- `ledger-consistency-guard`: 对账命令新增实例不变量；存量期初对齐调整单；部署闸门（对账零差异含实例维度）
- `transfer-create-pages`: 领用创建页加库存来源选择；实例管理行的实例点选表格（归还/调拨/回收同）
- `fixed-asset-table-columns`: 列表列重塑（品目联查列 + 出生信息派生列 + 待补录标识）
- `fixed-asset-create`: 手动创建入口冻结（实例出生 = 采购单或存量迁移）
- `fixed-asset-import`: Excel 导入冻结（含 fa 模板校验/去重系列行为废止）
- `fixed-asset-export`: 导出列扩展（品目联查列 + 出生信息派生列）

## Impact

- 后端：`apps/assets/models.py`（FixedAsset 重塑 + InstanceSequence）、`apps/assets/services/`（新增 instances.py：编号生成/状态迁移，由 ledger.apply_document 调用）、`apps/assets/views.py`（FixedAssetViewSet 冻结与补录）、`apps/transfers/models.py`（领用来源、行实例关联、删文本列）、`apps/transfers/serializers.py`、`apps/transfers/views.py`（_apply_ledger 过渡删除逻辑下线）、`apps/assets/management/commands/check_ledger_consistency.py`
- 迁移风险：FixedAsset 同表加列+回填+删列、TransferLine 删列、Transfer 加列——PG 需 atomic=False 拆分（DML/DDL 分离，P1/第一刀前科）；编号不在字典的存量实例自动登记字典存根（第一刀先例）；迁移完成对账（数量+实例双不变量）必须零差异
- 前端：`src/views/FixedAssetList.vue` 重做、`FixedAssetCreate.vue` 下线（含路由/导航）、`src/views/transfers/**` 创建页与 `components/TransferLinesEditor.vue` 实例选择器、详情页实例列、移动端即时回收改实例引用
- 测试：`test_fixed_asset.py` 重写、`test_transfer_lines.py`/`test_ledger_contract.py`/`test_ledger_migration_and_guard.py` 扩展、`test_ledger_architecture.py` 扩展（FixedAsset 写操作白名单仅 services）
- 兼容性：审批流/权限操作码/数据范围不变；`manage_instances` 操作码（小案③已建）首次投入使用
