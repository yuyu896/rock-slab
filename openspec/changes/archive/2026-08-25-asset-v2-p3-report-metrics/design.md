## Context

设计书第九节 P3 行"报表口径切换"。摸底结论：后端口径自 P1 已正确（数量=台账三列、金额=已生效采购单明细行），问题全在前端展示层——假数据、死组件、错误字段映射（详见 proposal）。另外台账页有"是否充足"列但无筛选，报表"库存不足"指标没有下钻落点。

关键现状：

- `overview`（reports/views.py:101-153）已输出 totalAssets/totalValue/activeRate/growthRate（数量环比），growthRate 前端已用真值；缺 金额环比 与 不足行数。
- `by_branch`（:156-178）只出总量一列；分公司明细表的"使用中"列在前端拿占比×总数伪算。
- `by_category`（:209-231）完整却无人调用；环图取 `getCategories()` 的 `c.资产数量`——该字段随 V2 品目字典重构删除，环图恒空。
- `transfers`（:234-283）行字段为 date/docNumber/assetCode/assetName/fromBranch/toBranch/quantity/status/actionType，无 operator；前端表格按 `type`/`createdAt`/`创建人` 取值三列恒 "-"，趋势聚合把全部流水算进"调拨"。
- 台账 `AssetStock.生效警戒线` = 行级 警戒线 ?? item.warning_line（models.py property），DB 侧可用 F 表达式表达；台账筛选器无充足参数。
- 侧边栏"资产盘点"徽标（SidebarNav onMounted 拉 count）是现成的轻量数字徽标先例（刀三复用）。

## Goals / Non-Goals

**Goals:**
- 报表页每个数字都有真实来源：数量=台账、金额=采购明细行、趋势=流水聚合。
- 双口径切换：分公司排行 数量/价值 一键切换；金额口径全链路（排行/明细表/导出）一致。
- 库存不足可下钻：报表计数 → 台账页不足筛选。
- 无数据时空态，不再用示例数据填坑。

**Non-Goals:**
- 使用率环比（台账是时点快照，无历史快照可环比——移除假角标而非造一个真值；将来若做日终快照表再议）。
- 报表授权/明细行聚合口径（report-data-scoping 既有契约，不动）。
- 分类环图的金额口径（分类金额需按品目联采购明细行聚合，本轮只做数量口径；排行 tab 的金额切换仅分公司维度）。
- 新图表库/图表重构（沿用既有 DOM 条形图/环形图形态，只修数据与映射）。

## Decisions

**D1 金额口径的分公司归属 = 入库分公司（Coalesce(to_branch, from_branch)），聚合按明细行**
采购单的金额事实在明细行（铁律 #8），归属分公司取货物入库方。`by_branch` 先按台账 values('branch__name') 聚四列数量，再对已生效采购单 `values('to_branch','from_branch').annotate(Sum('lines__金额'))` 按入库分公司累加，Python 侧按分公司名合并（台账行是全集，采购金额并入同名项；金额仅来自已生效采购，与 overview totalValue 同源同过滤）。

**D2 lowStockCount 用 F 表达式行内比较，与 property 语义一字不差**
`Q(警戒线__isnull=False, 在库数量__lt=F('警戒线')) | Q(警戒线__isnull=True, item__warning_line__isnull=False, 在库数量__lt=F('item__warning_line'))`，count() 计行数。台账筛选参数 `sufficient=0` 用同一 Q（filters.py 提公共函数），避免两处各写一份漂移。

**D3 valueGrowthRate 与 growthRate 同构：本月 vs 上月采购金额，上月为 0 时本月>0 记 100**
复用 overview 既有环比代码形状（数量环比的金额版），口径注释写明"采购金额月环比"。不引入 dateRange 影响（环比固定取自然月；dateRange 仅作用于流水/明细类报表——页面文案注明台账数量为时点快照）。

**D4 趋势聚合桶：入库=采购+归还、出库=领用+回收、调拨=调拨，按明细数量求和**
以"库存维度变动方向"定义桶（采购/归还在库+、领用在库−、回收在用−、调拨位移），三桶与图例 入库/出库/调拨 对齐；月键取流水行 `date`（YYYY-MM-DD）前 7 位。空数据展示空态文案，删除示例数据 fallback。

**D5 变动明细表列定稿：单据编号/日期/操作类型/资产编号/资产名称/调出/调入/数量/审批状态/经办人**
后端 transfers 行补 `operator: t.创建人`（单头 CharField，现成）。前端列与后端字段一一对应，导出同映射；ACTION_TYPE 中文标签复用前端 constants 既有映射（无则在本文件补全量映射表，与后端 choices 对齐）。

**D6 "库存不足"下钻走路由查询参数 `/assets/summary?sufficient=0`**
AssetSummary 初始化读 `route.query.sufficient` 预置筛选下拉（全部/仅不足），下拉变更仍走既有 fetch。不新增跨页状态 store。

## Risks / Trade-offs

- [采购金额并入 by_branch 后，仅有台账无采购单的分公司金额显示 0] → 语义正确（无采购事实=0 金额），页面列头标"采购金额"而非"资产总值"消除歧义。
- [F 表达式跨 SQLite/PG 行为] → 纯比较无聚合无方言函数，两侧安全；进 pytest 双侧隐式覆盖（SQLite）+ 生产 PG 部署对账兜底。
- [使用率假角标移除后卡片信息量略降] → 真话优先；环比无来源的指标宁可不放。
- [删除示例数据后空库首屏趋势区空白] → 空态文案"暂无流水数据"，符合"无数据不装忙"原则。

## Migration Plan

纯读侧改动，无迁移无数据回填。部署即生效；回滚还原代码即可。

## Open Questions

无。
