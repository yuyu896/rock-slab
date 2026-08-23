# 设计：资产模型 V2 — P1 立契约

> 上游：`docs/design/asset-model-v2.md`。本文只做实施决策，需求见 proposal/specs。

## Context

现状（探察实证）：

- 三表（AssetStock / Asset / FixedAsset）零外键，靠 资产编号/分公司名/部门名 字符串匹配，存在跨分公司匹配与"全局首条"兜底
- 台账唯一写路径是回收审批（`transfers/views.py` `_apply_recovery_stock`）；采购/领用/归还/调拨只写 Asset；盘点审核直接改 Asset 数量；三条导入直插各自的表
- 无 services 层，写逻辑全部内联在各 ViewSet 私有方法
- `Category` 已有唯一 `asset_code` + 名称/类目/分类/单位/警戒线，缺 管理方式/规格/图片/是否租用/默认供应商；背着 4 个只统计 Asset 的反范式计数字段（信号驱动）
- 部门为纯文本散落 5 处（Asset/FixedAsset/Transfer×3）
- 前端有跨表编排：SummaryFillDialog 从台账行直接 createAsset

前置就绪：小案②③已完成（组织树唯一父级、岗位模板权限）；操作码 `manage_dictionary`/`adjust_ledger`/`dispose_assets` 已在 `permissions/operations.py` 落位。

## Goals / Non-Goals

**Goals:**

- 台账成为唯一库存事实源，`check_ledger_consistency` 全库零差异
- 五单 + 调整单对称联动，全部经唯一写入口
- 品目字典、部门字典落地；Asset 冻结只读；铁律入 CLAUDE.md

**Non-Goals:**

- 单据明细行化、前端流转页重做、实例层接入、Asset 物理退役、导航合并（P2）
- 处置单独立 UI、盘点差异自动生成调整单、待补录提醒、按管理方式分级审批（P3）
- 序列号"待补录"流、内部编号生成改造（P2，`count()` 竞态届时修）

## Decisions

### D1 品目字典：改造 Category，不新建模型

Category 的 `asset_code unique` 已是事实上的编号户籍，且被 Asset/FixedAsset/导入校验/lookup 四处字符串引用——新建模型需要迁移全部暗引用，收益为零。

- 新增：管理方式 `management_type`（quantity|instance，默认 quantity）、规格 `specification`（定义性，可空）、图片 `image`、是否租用 `is_rental`、默认供应商 `default_supplier`（仅预填便利）
- 下线：`asset_count`/`in_stock_count`/`asset_total_quantity`/`in_stock_quantity` 四个计数字段及 `signals.py` 计数信号——它们只盯 Asset 表，违反铁律 1"每样信息只存一处"；计数职责移交台账派生列
- `attribute_template` 保留不动，P2 实例层接入时再评估
- 字典管理页展示"分编号判定测试"三问提示（领用会挑规格吗/警戒线需分开吗/价格需分开核算吗）

### D2 台账模型：改造 AssetStock，行 = 分公司 × 品目

保留模型名与 API 路径（前端 `/assets/summary` 不变），字段重构：

- `branch` FK（PROTECT）+ `item` FK → Category（PROTECT），唯一约束 `(branch, item)` 取代现 `(分公司, 资产编号)` 文本约束
- 数量四维：在库数量（**唯一存储值**）、在用数量、回收库数量（后两者为 service 维护的物化派生列——事实源是单据流水，物化仅为直显与查询性能）、总量（serializer/annotate 计算，不落库）
- 警戒线：行级可空，空则取品目默认；是否充足为计算值
- 删除全部冗余文本列（资产编号/名称/规格/类目/分类/分公司名/编号）——serializer 联品目字典输出，前端字段兼容

### D3 唯一写入口：`assets/services/ledger.py`

- 台账数量的全部变动（五单审批、调整单、导入、期初入账）收敛到 service 函数，事务内 `select_for_update` 锁台账行后变动并重算派生列
- `transfers/views.py` 的 `_sync_*`/`_apply_*` 内联写逻辑全部改为调 service；匹配逻辑从"三级字符串 fallback"变为单据显式携带 branch/item 引用
- 架构测试执法：pytest 扫描 `backend/apps/**` 源码，台账数量写模式仅允许出现在 `services/ledger.py`、migrations、tests（设计书十.3）

### D4 五单联动语义（对照设计书 5.2）

| 单据 | 台账动作 | 校验 |
|---|---|---|
| 采购入库 | 在库+N | — |
| 领用 | 在库−N，在用+N | 在库≥N（行锁） |
| 归还 | 在用−N，在库+N | 默认回新品在库（已敲定） |
| 调拨 | 调出在库−N，调入在库+N（无行则建） | 调出在库≥N |
| 回收入回收库 | 在用−N，回收库+N | — |
| 回收直接处置 | 在用−N，总量−N | 记处置方式/金额 |

- 采购生成 FixedAsset 实例是 P2 的事，P1 保持现状（不生成）
- **语义收紧声明**：V2 回收固定从"在用"回收（设计书 5.2）。处置在库品 P1 暂无专门单据，临时走手工调整单（在库列减 + 事由），处置单 P3 独立
- Transfer 新增字段：回收去向（recycle_bin|dispose，默认 recycle_bin）、处置方式（出售/报废/捐赠）、处置金额

### D5 调整单：新模型 LedgerAdjustment，P1 不做审批流

- 字段：branch FK、item FK、目标列（在库/在用/回收库）、变动量（±N）、事由、经办人 FK、是否期初单（flag）、生效时间
- 直接生效（不走审批），权限用 `adjust_ledger` 操作码；完整调整单 UI 与审批流 P3 按需补
- 独立于 Transfer：调整不是流转，字段集不同；避免 Transfer 的 40 字段大杂烩再加码（明细行化 P2 再统一考虑）

### D6 存量迁移：Asset 聚合 + 期初调整单

- 源 = **Asset 表**（设计书十一；AssetStock 是回收路径维护的失真快照，Asset 是多数路径的事实记录）
- 纯 Python 聚合（禁 `min(uuid)` 等 DB 特定聚合——SQLite 绿/PG 炸的前科），按 (branch, 资产编号) 分状态桶：在库→在库列；使用中/维修中→在用列；报废→出局不计入
- 每聚合行生成一条期初 LedgerAdjustment（is_initial=True，事由"系统期初"），台账行由 service 入账——**对账公式由此无需期初特例**：台账列 == Σ单据流水，期初单吸收全部历史
- 资产编号不在字典的行、与旧 AssetStock 的数量差异行 → `preview_ledger_migration` 命令输出预览清单，人工确认/补字典后才执行 `migrate_initial_ledger`
- 历史 Transfer（期初单时刻之前）不参与对账——已被期初单吸收

### D7 Asset 冻结与下游读者

- Asset ViewSet 写方法全部下线（405），导入 action 下线（410），保留 GET；数据库不锁
- 流转审批不再写 Asset（联动全部改台账）；盘点 `_adjust_inventory` 的写操作移除，审核仅记录差异（**盘点 P1 降级为记录模式**，清单仍从 Asset 历史视图生成——P1 不重构盘点，P3 切台账+差异生成调整单）
- **报表切台账**（overview/by_branch/by_status/by_category 的 queryset 从 Asset 换 AssetStock；状态维度 = 在库/在用/回收库三列；购入金额从采购单聚合——金额属单据层，设计书 #8）。不切则上线即驾驶舱失明，切换成本（4 个聚合端点）可接受

### D8 对账命令

- `check_ledger_consistency`：逐行（branch×item×列）比对台账值 vs 流水重算值，输出差异表 + 计数，有差异 exit 1
- 流水 = 期初调整单（is_initial）+ 期初时刻之后的已通过 Transfer + 全部非期初调整单；期初时刻 = min(期初单生效时间)
- 进 pytest（构造漂移场景断言可检出）+ deploy.sh 在 migrate 后执行，非零退出中止部署

### D9 部门字典

- `Department(branch FK PROTECT, 名称)`，unique together (branch, 名称)，挂 organizations app
- 存量归一：命令扫描 5 处部门文本 distinct → 按分公司生成字典行，预览清单先行；分公司为空的行走清单人工判定
- P1 字段本体不改 FK（文本保留），字典先立；P2 领用单绑部门时 FK 化（设计书依赖：部门字典→P2）
- options 端点改读字典；流转创建页三处部门输入、固定资产创建页部门输入接字典下拉

### D10 铁律入 CLAUDE.md

CLAUDE.md 增"铁律"节，原文照录设计书二节两条铁律 + 提案审查两问（是否让某类信息存了两份 / 数量变动是否走单据）。

## Risks / Trade-offs

- [存量迁移不可逆] → 部署前全量备份；预览清单人工确认；迁移后立即对账
- [报表口径变化（维修中/报废桶消失，总量=三列之和）] → 上线说明；报废存量本就出局
- [回收语义收紧，在库处置无专门单据] → 临时走手工调整单留痕；P3 处置单
- [盘点降级为记录模式] → 有意取舍（P1 范围控制）；P3 完全体
- [Asset 冻结冲击未知调用方] → 仅 API 层冻结；观察上线后 410/405 日志
- [架构测试文本扫描有漏报] → 哨兵定位，配合 code review；不追求完备

## Migration Plan

1. 全量备份（pg_dump）
2. 部署代码 + migrate（结构迁移：字典字段/台账新结构/部门/Transfer 新字段——台账数据迁移此步不清数据）
3. `python manage.py preview_ledger_migration` → 人工审清单（未登记编号/分桶统计/与旧台账差异/部门归一清单）
4. 补字典或修数据 → `python manage.py migrate_initial_ledger`（聚合 + 期初单 + service 入账 + 部门归一）
5. `python manage.py check_ledger_consistency` 零差异 → 放行
6. 回滚 = 恢复备份 + 回滚代码（数据迁移向前不可逆，无 down 迁移）

## Open Questions

（无——两个 P1 待确认点已于 2026-08-23 敲定并落痕设计书十二节：回收拆两去向；归还默认回新品在库、可配置延至 P3。）
