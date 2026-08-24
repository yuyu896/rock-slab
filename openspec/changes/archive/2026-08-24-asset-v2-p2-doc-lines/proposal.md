# 提案：流转单明细行化（资产模型 V2 · P2 第一刀）

## Why

总设计书（docs/design/asset-model-v2.md）核心决策 #5：流转单必须"单头（谁/何时/为何）+ 明细行（品目×数量）"结构，一张采购单含全部物品。现状是 `Transfer` 一行一件的平铺模型——一张采购单 10 种物品要建 10 张单、走 10 次审批；品目信息（编号/名称/规格/类目）在单据上手抄存储，违反铁律 1"每样信息只存一处"。这是 P1 立契约后资产模型 V2 手术期的第一刀，也是实例层接入（P2 第二刀）的前置结构。

## What Changes

- 新增 `TransferLine`（明细行）模型：品目 FK（→品目字典，PROTECT）、数量、本批规格（记录性）、单价/金额（采购）、存放位置（回收）；单头保留"谁/何时/为何/审批"及类型专属字段（供应商、回收去向等）
- 单头新增 `单据编号`（类型前缀 + 日期 + 日内序号，行锁计数器生成，杜绝 count() 并发竞态）
- 台账唯一写入口 `ledger.apply_document` 改为按明细行迭代执行联动矩阵，同一单据所有行在同一事务内变动，行锁按 (branch, item) 排序防死锁；充足性不足整单回滚
- **BREAKING** 单据创建 API（purchase/assign/return/transfer/recovery 五个 action）payload 改为 `{...单头, items: [...]}`，不再接受平铺品目字段
- **BREAKING** 存量 `Transfer` 的品目级平铺列（资产编号/资产名称/规格型号/调拨数量/单价/总金额/单位/资产类目/物品分类/固定资产内部编号/存放位置）迁移入明细行后**删除**——不保留双份存储（铁律 1），杜绝漂移回归
- 存量迁移：每张历史单据生成 1 条明细行；编号不在字典的历史单据自动登记字典存根行（编号户籍原则）
- 消费方全部改为按行取数：对账命令 `check_ledger_consistency`（迁移前后必须零差异）、报表聚合、通知 payload、Excel 导出（一行明细一行输出）、Excel 导入（一行=一单一行，行为不变）
- 前端流转页重做：创建页改"单头表单 + 可增删的明细行表格"（品目字典点选，禁手抄编号）；详情页 = 一行元信息 + 明细表（设计书决策 #11）；列表页按单头粒度展示（单号/类型/日期/分公司/品目数/总数量/状态）

不在本刀范围（后续提案）：实例层接入与领用绑实例（P2 第二刀）、Asset 退役与导航合并（P2 第三刀）、独立处置单（P3）、盘点差异联动调整单（P3）。明细行预留实例引用扩展位（本刀不加列）。

## Capabilities

### New Capabilities
- `transfer-line-items`: 流转单单头+明细行结构——数据模型、单据编号、创建/详情/列表 API 形状、明细行校验（品目必为字典登记、数量为正、重复品目行合并规则）、存量迁移与平铺列删除

### Modified Capabilities
- `document-ledger-sync`: 五单台账联动矩阵从"按单据品目字段"改为"按明细行迭代"；充足性校验与行锁以行为粒度，任一行不足整单回滚
- `transfer-create-pages`: 创建页从单物品表单改为"单头 + 明细行表格"，品目选择从手抄/输入改为字典点选
- `transfer-batch-import`: 导入行落库为"单头+单明细行"，校验口径与错误提示不变
- `transfer-export-filter`: 导出按明细行展开输出（单头信息随行重复），模板列不变
- `report-data-scoping`: 报表数量聚合从 Transfer 平铺列改为 TransferLine 联查
- `notification-data-scoping`: 流转单通知 payload 从单品目改为明细摘要（首行品目 + 共 N 项）

## Impact

- 后端：`apps/transfers`（models/serializers/views/migrations）、`apps/assets/services/ledger.py`（唯一写入口签名）、`apps/assets/management/commands/check_ledger_consistency.py`、`apps/reports/views.py`、`apps/notifications/signals.py`
- 迁移风险：存量数据搬迁 + 删列，PG 生产部署需 atomic=False 拆分（DML 先行、DDL 删列随后，沿用 P1 经验）；迁移完成即跑对账命令验证零差异
- 前端：`src/views/transfers/**`（创建/详情/列表页重做）、`src/api/transfers.ts`、`src/types`、`src/constants`（单据状态不变）、移动端涉及流转创建的页面同步改
- 测试：transfers/ledger 现有用例改造为多明细形状，新增多行单据、部分行不足整单回滚、迁移前后对账零差异用例；架构测试（唯一写入口）不放松
- 兼容性：单据审批流（待审批/已通过/已驳回/已入库）、权限操作码、数据范围过滤行为不变
