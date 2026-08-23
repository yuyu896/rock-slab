# 提案：资产模型 V2 — P1 立契约

> 上游依据：`docs/design/asset-model-v2.md`（总设计书）第九节 P1 行。本提案为三阶段主干的第一期。

## Why

总设计书病根诊断已在代码中实锤：**台账（AssetStock）全库只有回收审批一条写路径**——采购入库不写台账、领用/归还/调拨只动 Asset、盘点审核直接改 Asset、三条导入各自直插各自的表。数量事实存了三份、写入方各动各的子集，漂移必然发生且不可发现。三表之间零外键，仅靠 资产编号/分公司名/部门名 字符串匹配对齐（且存在跨分公司匹配、全局首条兜底等脆弱逻辑）。P1 的任务是把"同一件事实只存一处"立为系统契约：台账成为唯一库存事实源，所有数量变动收敛到唯一写入口，机器对账兜底。前置小案①②③（布局/组织树/权限）已完成，依赖就绪。

## What Changes

- **品目字典**：`Category` 升级为品目户口本——新增 管理方式(数量|实例)、规格(定义性)、图片、是否租用、默认供应商 5 字段；下线 4 个只统计 Asset 的反范式计数字段与信号；字典管理页加"分编号判定测试"提示
- **台账唯一事实源**：`AssetStock` 重构为一行 = 分公司 × 品目（双 FK + 唯一约束），在库为唯一存储值，在用/回收库/总量为服务层维护的派生列；冗余文本字段（资产名称/规格/类目）改为联字典显示
- **五单对称联动**：采购/领用/归还/调拨/回收 审批通过后统一经 ledger service 写台账（对照设计书 5.2 单据×数量表）；回收单增加去向二选一（入回收库/直接处置）；领用校验在库充足、调拨校验调出在库充足
- **调整单**：新增第六种单据类型（铁律2 的合规出口），手工修正与导入增量的载体
- **存量迁移**：Asset 表按 (分公司, 资产编号, 状态分桶) 纯 Python 聚合（禁用数据库特定聚合）生成新台账行 + **期初调整单**，使对账公式无需期初特例；不在字典的编号出预览清单人工确认
- **导入改增量**：台账导入从直插改为生成调整单（预览差异→确认→入账）；**BREAKING** 资产明细导入随 Asset 冻结下线；固定资产导入维持现状（P2 实例层接入时改造）
- **Asset 冻结只读**：**BREAKING** Asset 全部写接口（POST/PUT/PATCH/DELETE）返回 405/403，仅保留 GET；流转审批不再写 Asset；盘点审核不再直接改 Asset 数量（差异仅记录，P3 接调整单）；"从台账填入资产明细"前端跨表编排下线
- **部门字典**：新建 `Department`（分公司 × 部门名，unique together），存量 5 处部门纯文本归一迁移（预览清单）
- **机器执法**：`check_ledger_consistency` 管理命令（台账四列 == 单据流水重算）进 pytest 与部署检查；ledger service 为台账数量唯一写入口；架构测试断言 services 之外无台账写操作
- **铁律入 CLAUDE.md**：两条铁律写入项目宪法，全项目强制

## Capabilities

### New Capabilities

- `item-dictionary`: 品目字典——编号户籍（唯一约束）、管理方式判定、字典管理页字段与提示
- `ledger-single-source`: 台账唯一事实源——行粒度（分公司×品目）、在库唯一存储值 + 三派生列、唯一约束、字段联字典显示
- `document-ledger-sync`: 五单 + 调整单对台账的对称联动契约（单据×数量对照表、充足性校验、回收二去向）
- `ledger-consistency-guard`: 机器执法——对账命令、唯一写入口、架构测试、部署检查挂钩
- `asset-freeze-readonly`: Asset 冻结只读——写接口下线、流转/盘点不再写 Asset、导入下线
- `department-dictionary`: 部门字典——模型、管理接口、存量文本归一迁移
- `initial-ledger-migration`: 存量迁移——Asset 聚合分桶、期初调整单、预览清单确认流

### Modified Capabilities

- `asset-summary`: 台账数据模型四列化与品目 FK 化；台账管理接口写操作收敛到调整单；删除"从台账填入资产明细与固定资产"能力
- `transfer-asset-sync`: 五单联动目标从"直写 Asset/FixedAsset 字符串匹配"改为"经 ledger service 写台账"；FixedAsset 生成/退役留待 P2
- `transfer-stock-link`: 领用扣减/调拨双边变动的语义基准从 Asset 数量改为台账在库列
- `category-counter-signal`: 反范式计数字段与只盯 Asset 的计数信号下线，计数职责移交台账派生列
- `category-quantity-count`: 同上（计数字段下线）
- `asset-department-options`: 前端常量预置部门方案废止，由部门字典接管所有部门输入
- `transfer-asset-sync`: 五单直写 Asset/FixedAsset 的旧联动契约整体废止，由 `document-ledger-sync` 承接
- `transfer-stock-link`: 领用/调拨以 Asset 数量为基准的旧联动契约废止，由 `document-ledger-sync` 承接

## Impact

- **后端模型迁移**：`Category` 加 5 字段删 4 计数字段；`AssetStock` 重构（数据迁移）；`Transfer` 加 回收去向/处置方式/处置金额/调整事由 字段；新 `Department`、`LedgerAdjustment`（或并入 Transfer）；期初调整单数据迁移
- **后端代码**：新 `assets/services/ledger.py` 唯一写入口；`transfers/views.py` 五个 `_sync_*`/`_apply_*` 内联方法改为调 service；`assets/views.py` 台账导入重写、Asset 写接口冻结；盘点 `_adjust_inventory` 写操作移除；`check_ledger_consistency` 命令；架构测试
- **前端**：台账页（四列+联字典显示）、字典管理页（新字段+判定提示）、部门字典管理、资产列表页只读化、台账导入对话框（差异预览）、回收单创建页（去向二选一）
- **部署**：deploy.sh 增加对账检查步骤；上线前全量备份先行（设计书十一）
- **风险**：一次性数据迁移不可逆（需备份+预览清单）；台账写接口语义变化影响所有依赖 Asset 数量的既有功能（报表 P1 暂维持读 Asset，P2 切换——见 design.md 决策）
