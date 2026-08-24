# 设计：Asset 表退役与导航合并（P2 第三刀）

## Context

Asset 自 P1 冻结只读，字段三分搬迁已完成且对账零差异；盘点模块（InventoryItem/InventoryCheck FK→Asset）是最后运行时依赖。前端资产明细页（/assets/list）是冻结视图的 UI 壳，台账页（/assets/summary）已是库存唯一展示口径。

## Goals / Non-Goals

**Goals:** Asset 物理退役；盘点明细基准换为台账行；台账页成为资产主视图（实例下钻）；移动端资产查询切台账口径。
**Non-Goals:** 盘点差异联动调整单（P3）；实例批量退役；报表改版；盘点 UI 重做（仅适配新字段名）。

## Decisions

### D1 盘点明细 FK：asset → stock（AssetStock）

盘点盘的语义对象就是「某分公司 × 某品目」的库存行：expected_qty=在库数量，差异=实盘 vs 在库。InventoryCheck 同步换列（经 item 传递，check 自身 asset 列换 stock）。存量迁移：按 (task.branch, asset.资产编号→item) 解析 AssetStock 行；解析不到（无台账行/无品目）的盘点项与关联 check 删除并输出计数——这类行在 P1 台账口径下本就不存在，属脏数据。盘点项唯一约束 (task, stock) 防重。

### D2 期初工具退役，增量导入为唯一期初入口

preview/migrate_initial_ledger 以 Asset 为源造期初，Asset 亡则工具亡。新环境期初=台账增量导入（P1 已交付：默认差异预览、confirm 逐行生成 is_initial 调整单）。对账命令「未初始化容忍」提示文案同步改。

### D3 台账主视图的实例下钻形态

台账行（实例管理品目）操作列加「实例」按钮 → 抽屉内嵌该 (分公司×品目) 实例列表（内部编号/序列号/状态/使用人 + 补录 + 生平链接），复用既有实例 API（asset_code + branch 筛选）与 InstancePicker 同源数据。不新做后端端点。独立页 /fixed-assets 保留为实例档案管理深入口（更名「实例档案」）。

### D4 Asset 表 DROP 而非留壳

铁律 1：留壳=第三份存储诱惑。DROP 前置条件已满足（P1 验收零差异、冻结期无人写入）。迁移顺序：盘点 FK 切换（D1）→ Asset DeleteModel；全链 DDL/DML 按 PG 分片惯例拆分。

## Risks / Trade-offs

- [历史盘点项解析失败被删] → 仅删无台账对应的脏行并输出计数；盘点报告的编号/名称可经 stock.item 联查恢复语义
- [/api/assets/ 404 波及未知调用方] → 前端全量切换 + 三个子路由（summary/fixed-assets/调整单）不受影响；移动端同步改
- [移动端扫码查资产口径变化] → 扫码输入按编号先查实例（贵重）再查台账行（数量），结果页标注口径
