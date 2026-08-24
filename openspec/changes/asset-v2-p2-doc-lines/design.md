# 设计：流转单明细行化（P2 第一刀）

## Context

P1 已立契约：品目字典是编号户籍、台账是唯一库存事实源、`ledger.apply_document` 是唯一写入口、对账命令机器执法。但单据本体仍是 `Transfer` 一行一件的平铺模型（约 40 个字段混杂单头与品目信息），一张采购单多种物品要建多张单。前端已经长出两个"多行 UI"补丁——`AssignCreate.vue` 的 items 数组（提交时逐行发 N 个请求）和旧版 `purchases/PurchaseCreateForm.vue` 的多行表单（循环调 `purchaseAsset`）——证明多明细单据是真实需求。领用单的"使用人"目前拼进备注字符串（`使用人: xxx`），无字段承载。

消费方现状：对账命令按 `t.资产编号/t.调拨数量` 重算流水；报表 `Sum('调拨数量')`；通知 payload 取单品目字段；Excel 导入一行=一单、导出按单平铺。

## Goals / Non-Goals

**Goals:**

- `Transfer`（单头）+ `TransferLine`（明细行）双模型落地，品目信息只存 FK，删平铺列（铁律 1）
- 单据编号可读可引用（Excel 思维），并发安全生成
- 唯一写入口按行迭代执行联动矩阵，多行单据原子生效，任一行不足整单回滚
- 存量 1:1 迁移零语义变化：迁移后 `check_ledger_consistency` 仍零差异
- 前端：创建页"单头表单 + 明细行表格"、品目字典点选；详情页 = 一行元信息 + 明细表（决策 #11）
- 消费方（对账/报表/通知/导入导出）全部改为按行取数

**Non-Goals:**

- 实例层接入、领用绑实例、Asset 退役、导航合并（P2 第二、三刀）
- 独立处置单、盘点差异联动调整单、按管理方式分级审批（P3）
- `调出/调入分公司` 文本列与 FK 双存的去重（既有债务，本刀不动；分公司文本列保留原行为）
- 回收去向/处置方式/处置金额下沉到行（本刀维持单头一份，P3 独立处置单时再议）
- 导入按单头字段分组合并多行为一单（导入仍一行=一单一行）
- 审批流、权限操作码、数据范围规则的变化

## Decisions

### D1 模型：保留 `Transfer` 名作单头，新增 `TransferLine`

改名 `TransferDocument` 会波及 URL、审计装饰器、related_name、数十个测试，收益仅是语义命名。保留 `Transfer` 作单头，新增 `TransferLine`：

```
TransferLine(UUIDModel, TimestampedModel):
    transfer   FK→Transfer, on_delete=CASCADE, related_name='lines'
    item       FK→Category(品目字典), on_delete=PROTECT
    行号        IntegerField（创建时顺序赋值，稳定排序，UUID 主键不可排序）
    数量        PositiveIntegerField()
    本批规格    CharField(blank)          # 记录性（决策 #9），区别于字典定义性规格
    单价/金额   DecimalField(null)        # 采购行
    使用人      CharField(blank)          # 领用行，记录性文本（决策 #12），终结备注拼串 hack
    department FK→Department(null, PROTECT)  # 领用行
    存放位置    CharField(blank)          # 回收行
    固定资产内部编号 CharField(blank)     # 回收即时处置桥（P2 二刀改实例 FK）
```

同品目重复行允许、语义相加（不静默合并——合并会改写用户意图；台账按行迭代天然正确）。

### D2 单头字段去向表

| 去向 | 字段 |
|---|---|
| 保留单头 | 调拨日期（值语义即单据日期，**不改名**避免全链路抖动）、调出/调入分公司（文本+FK 双存照旧）、调出/调入部门、调出/调入负责人、调拨原因、备注、审批状态/人/时间、创建人、action_type、供应商、需求部门、采购经办人、用途、回收分类、回收去向、处置方式、处置金额、出库日期 |
| **新增单头** | 单据编号 |
| 迁入明细行后删除 | 资产编号、资产名称、规格型号、调拨数量、单价、总金额、单位、资产类目、物品分类、存放位置、固定资产内部编号 |

删除列的理由：名称/规格/单位/类目由 `item` FK 联字典派生（ledger-single-source 已确立同款模式）；保留即双存储，违反铁律 1，且旧列无人维护必然漂移。

### D3 单据编号：类型前缀 + 日期 + 日内序号

`单据编号 = {CG|LY|GH|DB|HS}{YYYYMMDD}-{三位序号}`（采购/领用/归还/调拨/回收）。新模型 `DocumentSequence(type, date, last_no)`，生成时 `select_for_update` 锁计数行自增——与台账行锁同一并发模式，杜绝 count() 竞态（设计书 5.3 对内部编号的告诫同样适用）。存量迁移按 created_at 分组回填编号。不用 UUID 片段：用户要以单号口头/Excel 引用单据。

### D4 唯一写入口：先排序锁全部相关台账行，再按行迭代

`ledger.apply_document(transfer)` 重构为两阶段：

1. 收集单据全部行的 `(branch, item)` 对（调拨单含双边），排序后一次性 `select_for_update` 锁齐——避免两张多行单据交叉锁定死锁（A 锁 X 等 Y，B 锁 Y 等 X）
2. 按 `行号` 顺序逐行执行现行联动矩阵（矩阵本身一字不变），复用已锁行

充足性不足仍抛 `LEDGER_INSUFFICIENT`（错误信息带行号定位到明细行），调用方事务整体回滚——"部分生效"不存在。架构测试（services 之外无台账写）不放松。

### D5 API 形状：五 action 保持路径，payload 换 `{...单头, items: [...]}`

```
items: [{ item: <品目uuid>, 数量, 本批规格?, 单价?, 金额?, 使用人?, department?, 存放位置?, 固定资产内部编号? }]
```

- 品目引用一律 uuid（前端字典点选天然有；导入/移动端先 `lookupCategoryByCode` 解析）。不再接受手抄编号创建——未登记编号在序列化层即拒（相近编号提示沿用 P1 的 `suggest_similar_codes`）
- 校验：`items` 非空、每行数量 ≥ 1；类型维度规则沿用（领用需调出方、调拨双分支公司且不同、回收需调出方等）
- 响应 serializer：单头 + 嵌套 lines，行内联查输出字典回显（编号/名称/规格/单位/类目/管理方式），前端不二次查询
- `updateTransfer`（驳回编辑）：单头 PATCH + items 整体替换（先删后建，重排行号）
- `draft` / `immediate`（行内即时回收）语义不变，immediate 时行内 `固定资产内部编号` 按行触发 FixedAsset 删除（P1 过渡行为照旧，二刀改状态退役）
- **已生效单据禁删**（`perform_destroy` 拒绝 已通过/已入库）：生效单据是流水事实源，删除即破坏对账（平铺模型下已存在的漏洞，本刀顺手封死）

### D6 前端重做：一套明细行编辑器，四类型参数化

- **类型层**：新增 `TransferDocument` / `TransferLine` 类型；`TransferActionType`、`APPROVAL_STATUS_*` 不变；`TRANSFER_TYPES` 从 `useTransferList.ts` 移入 `constants`（与后端 action 对齐，补 'return'）。分公司字段新代码统一 `fromBranch/toBranch`（id）+ 后端回显名称，不再新增中文分公司键
- **ItemPicker 组件**：品目字典远程搜索点选（编号/名称检索，选中回显规格/类目/管理方式），替换"手抄编号 + 失焦反查"（`useAssetCodeAutofill` 退役）；AssignCreate、MobileAssign 等复用
- **TransferLinesEditor 组件**：可增删行表格，行内 ItemPicker + 数量 + 类型专属列（采购：单价/金额；领用：使用人/部门 DepartmentSelect；回收：存放位置/内部编号；调拨：本批规格）。四创建页 = 单头表单（既有字段不动）+ 此编辑器；`TransferCreateLayout` 扩展承载
- **AssignCreate** 现有 items 多行 UI 顺势改为一次提交一张多行单据（N 请求 → 1 请求）
- **详情页**：统一为"一行元信息 + 明细表"；回收补 `:id` 详情页，列表弹窗退役
- **列表页**：单头粒度列（单号/日期/分公司/品项数/总数量/状态/操作）；`assetCode` 筛选与关键字搜索改为联查明细行
- **旧版采购页清退**：`views/Purchase.vue`、`purchases/PurchaseCreateForm.vue`、路由 `/assets/purchase` 删除并重定向到 `/transfers/purchase`（其多行表单正是本刀转正的能力；`PurchaseImportDialog` 保留）
- **移动端**：MobileAssign / MobileTransfer 改 items payload（单行单据 UI 可接受）
- 其他消费方回归：Dashboard、AssetList（按品目查关联单据→联行）、Approval* 移动页

### D7 消费方按行取数

- **对账命令**：流水重算改 `Transfer.objects.prefetch_related('lines__item')`，逐行 bump；迁移前后各跑一次，零差异是验收线
- **报表**：`Sum('调拨数量')` → `TransferLine` 联查聚合（按 action 过滤经 transfer）；明细列表一行明细一行输出
- **通知**：payload 摘要化——首行品目名称 +（N>1 时）`等 N 项`，数量为各行合计
- **导出**：模板列不变，值改为行级（单位/类目联字典），单头信息随行重复
- **导入**：一行=一单一行，分支校验/编号户籍校验/相近编号提示照旧；采购行单价/总金额、回收行存放位置落行

### D8 迁移：DML 与 DDL 分离（PG 前科防范）

1. `0002_transferline_and_backfill`（`atomic=False`）：建 `TransferLine`/`DocumentSequence` 表；逐张历史单据建 1 行（行号 1，数量/规格→本批规格/单价/金额/存放位置/内部编号照抄）；品目解析按编号查字典，**未登记编号自动建字典存根行**（名称取单据资产名称、单位 '件'、资产类目 '未分类'）——编号户籍原则下历史编号必须入籍，比丢行或可空 FK 更诚实；回填单据编号
2. `0003_drop_flat_columns`：删除 D2 表中"迁入明细行后删除"列
3. 配套 `preview_doc_line_migration` 命令：列出未登记编号清单与影响单据数，供部署前人工过目
4. 部署顺序：备份全量 DB → migrate → `check_ledger_consistency`（零差异才放行，deploy.sh 已挂钩）

**回滚策略**：删列不可逆，回滚 = 还原全量备份（deploy.sh 部署前备份已是中国站惯例，任务清单中显式确认）。

## Risks / Trade-offs

- [PG 迁移 DML+DDL 同表炸 pending trigger events] → DML/DDL 拆两个迁移，DML 侧 `atomic=False`（P1 实战结论）
- [删列后遗漏某个消费方（报表/通知/移动端/测试 fixture）运行时才爆] → 全库 grep `资产编号|调拨数量` 等列名清点消费方（proposal Impact 已列）；后端测试全量跑 + 前端 vitest + build 类型检查兜底
- [多行单据交叉锁定死锁] → D4 排序预锁；并发审批测试覆盖（两张多行单据同时过审）
- [单据编号生成成为创建热点] → 锁粒度为 (类型, 日期) 行，跨类型/跨日无竞争；单日单类超千单才可能感知，当前量级无虞
- [存量单据含未登记编号，自动存根污染字典] → 存根字段明显可辨（'未分类'），preview 命令暴露清单供事后清理；宁可见不可丢
- [前端四套页面重做量大，回归面广（含移动端与 Dashboard）] → 复用 `useTransferList` 参数化模式；分类型逐页改造逐页可验；旧版采购页清退减少一套重复面
- [分公司文本/FK 双存保留] → 明知的债务：本刀聚焦品目级去重，分公司去重牵动组织改名级联，留给后续提案
- [驳回编辑整替 items 使"改一行"变"全单重录"体验] → 前端编辑态预填全部行，用户改哪行提交哪行，感知不变；后端整替保证原子性

## Open Questions

（无——回收去向/处置字段是否下沉到行、导入是否分组并单，均已列入 Non-Goals 有主。）
