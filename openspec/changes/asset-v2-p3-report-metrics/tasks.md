## 1. 后端

- [x] 1.1 `assets/filters.py` 提公共 `insufficient_stock_q()`（F 表达式：行级警戒线优先、空回落品目默认），`AssetStockFilterSet` 加 `sufficient` 参数（'0'=仅不足）
- [x] 1.2 `reports/views.py` overview：加 `lowStockCount`（insufficient_q 计数）与 `valueGrowthRate`（本月 vs 上月采购金额环比，上月在库为 0 时本月>0 记 100）
- [x] 1.3 `reports/views.py` by_branch：每分公司返回 stock/inUse/recycle/value 数量四列 + amount 采购金额（已生效采购按明细行金额、入库分公司 Coalesce(to,from) 归属，与台账行按名合并）
- [x] 1.4 `reports/views.py` transfers 行加 `operator`（t.创建人）
- [x] 1.5 后端测试：overview 不足计数与金额环比、by_branch 多分公司多明细行金额、流水行含经办人、sufficient 筛选（含行级/品目默认两级警戒线）

## 2. 前端

- [x] 2.1 `api/reports.ts` 与 `types/index.ts`：BranchStat 扩展（stock/inUse/recycle/amount）、ReportOverview 扩展（lowStockCount/valueGrowthRate）、流水行类型补 operator/docNumber
- [x] 2.2 指标卡修真：总值增速接 valueGrowthRate；库存不足接 lowStockCount 且"立即查看"跳 `/assets/summary?sufficient=0`；移除使用率假趋势角标
- [x] 2.3 分公司排行"数量/价值"tab 接线（价值=采购金额，formatMoney 展示）
- [x] 2.4 分类环图改接 `getByCategory`，移除 getCategories/资产数量 依赖；环心与图例随数据
- [x] 2.5 月度趋势重聚合：按流水行 date 前 7 位分月、actionType 分桶（purchase/return→入库，assign/recovery→出库，transfer→调拨）按 quantity 求和；删示例数据 fallback 改空态
- [x] 2.6 详细报表表：分公司 tab 展示 在库/在用/回收库/总量/采购金额/占比 真实列；分类 tab 展示 by_category 表；变动明细 tab 按真实字段渲染（单据编号/日期/操作类型中文/调出/调入/数量/状态/经办人）；状态色 key 对齐 在库/在用/回收库
- [x] 2.7 导出映射与页面表格一致（分公司含金额列、变动明细含经办人/单据编号）
- [x] 2.8 `AssetSummary.vue`：加"是否充足"筛选下拉（全部/仅不足），初始化读 `route.query.sufficient` 预置
- [x] 2.9 前端 vitest：报表页无硬编码假数据（12/+12.3%/+2.1% 不复现）、tab 切换数值源切换、环图数据来自 by_category、趋势空态；AssetSummary 读查询参数预置筛选

## 3. 验收

- [x] 3.1 后端 pytest 全绿、前端 vitest 全绿、`npm run build` 通过
