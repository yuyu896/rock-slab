# report-metrics Specification（新增）

## ADDED Requirements

### Requirement: 报表双口径输出

报表接口 SHALL 同时输出数量与金额双口径：数量口径 = 台账三列（在库+在用+回收库，时点快照）；金额口径 = 已生效采购单按明细行 `金额` 求和（铁律 #8，金额属单据层），归属入库分公司。`by_branch` 每分公司 MUST 返回 在库/在用/回收库/总量 数量与采购金额；`overview` MUST 返回 totalAssets/totalValue/activeRate/growthRate（数量月环比）/valueGrowthRate（采购金额月环比）/lowStockCount（在库数量低于生效警戒线的台账行数）；调拨流水报表行 MUST 含经办人（单头创建人）。双口径 MUST 经统一数据范围过滤（report-data-scoping 既有约束），金额聚合 MUST 以明细行为口径。

#### Scenario: 分公司双口径一次返回

- **WHEN** 分公司 A 台账（在库 5/在用 3/回收库 2）且有两张已生效采购单（明细行金额 100 与 50，入库分公司均为 A）
- **THEN** by_branch 中 A 行：总量 10、在库 5、在用 3、回收库 2、采购金额 150

#### Scenario: 金额按明细行聚合

- **WHEN** 一张采购单含两条明细行（金额 100 与 50）
- **THEN** 该分公司采购金额计 150，MUST NOT 按单头重复或漏计

#### Scenario: 库存不足行数

- **WHEN** 台账含 3 行在库数量低于生效警戒线（行级优先、空则品目默认）
- **THEN** overview.lowStockCount 为 3

#### Scenario: 流水行含经办人

- **WHEN** 请求调拨流水报表
- **THEN** 每行含 operator 字段（该单创建人），前端明细表不再出现恒空的经办人列

### Requirement: 报表页真实数据契约

报表前端 MUST NOT 展示硬编码数值或派生自错误字段映射的数值；每个指标、图表、表格列 MUST 来自后端真实响应字段；无数据时 MUST 展示空态。具体：指标卡总值增速用 valueGrowthRate、库存不足用 lowStockCount（无真实来源的环比角标 MUST 移除而非展示假值）；分公司排行"数量/价值"切换 MUST 接线（价值=采购金额）；资产分类分布 MUST 以 by_category 为数据源；月度趋势按流水正确字段聚合（入库=采购+归还、出库=领用+回收、调拨=调拨，按数量求和）且无数据时空态；变动明细表列与流水报表行字段一一对应；状态分布颜色键与台账三态（在库/在用/回收库）一致；导出行映射与页面表格一致。库存不足指标 SHALL 提供下钻：跳转台账页并预置不足筛选（`sufficient=0`：在库数量 < 生效警戒线）。

#### Scenario: 无假数据残留

- **WHEN** 打开报表页
- **THEN** 页面不出现硬编码的增速/占比/计数（如 +12.3%、+2.1%、固定 12），所有数字随接口数据变化

#### Scenario: 数量与价值切换

- **WHEN** 用户在分公司排行点击"价值"tab
- **THEN** 条形图与数值切换为各分公司采购金额，点"数量"切回总量

#### Scenario: 环图有数

- **WHEN** 台账存在多个资产类目的行
- **THEN** 资产分类分布环图与图例展示各类目数量与占比（来自 by_category）

#### Scenario: 趋势无流水时空态

- **WHEN** 时间范围内无任何流转单
- **THEN** 月度趋势区展示空态文案，MUST NOT 展示示例数据

#### Scenario: 库存不足下钻

- **WHEN** 用户点击指标卡"库存不足"的"立即查看"
- **THEN** 跳转台账页且列表已按"仅不足"过滤，行数与指标卡计数同口径
