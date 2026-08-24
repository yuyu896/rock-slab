# 提案：Asset 表退役与导航合并（资产模型 V2 · P2 第三刀）

## Why

总设计书决策 #4 与第八节：Asset 表 P1 起冻结只读，其字段已按品目/实例/流水三分搬迁完毕（字典/台账/单据承载），物理退役时机成熟；导航上「资产明细/固定资产表」两页应合并为「台账主视图 + 实例下钻」，员工不再面对三张口径不一的资产页。盘点模块是 Asset 的最后运行时依赖（InventoryItem/InventoryCheck FK 到 Asset），本刀一并改为挂台账行（AssetStock）——盘点盘的就是库存事实源，语义归位。

## What Changes

- **BREAKING** Asset 模型/表/API 物理退役：删 Asset 模型与迁移、AssetViewSet（冻结只读视图）、AssetSerializer/FilterSet、admin 注册；`/api/assets/` 主路由下线（summary/fixed-assets 子路由不受影响）
- 期初工具退役：`preview_ledger_migration`/`migrate_initial_ledger` 命令删除（依赖 Asset 造数）；对账命令「未初始化」提示改指台账增量导入（唯一期初入口）
- **盘点改挂台账行**：InventoryItem/InventoryCheck 的 `asset` FK → `stock` FK（AssetStock，分公司×品目）；生成盘点项从台账行出发（应盘数量=在库数量）；盘点提交按 stock 定位；存量盘点项按 (任务分公司, 资产编号) 解析迁移，解析不到的删除（输出计数）
- 前端：资产明细页（AssetList/AssetCreatePage/AssetImportDialog）下线，路由重定向到台账；侧边栏「资产明细」入口删除，「固定资产表」更名「实例档案」；**台账页升级为主视图**——实例管理品目行新增实例下钻（各状态计数 + 抽屉实例列表，含补录/生平入口）
- 移动端：资产查询/详情/扫码改走台账与实例接口（口径=台账行）
- 测试：Asset 相关用例改造/退役（18 个文件涉及），盘点用例改台账造数

不在本刀范围：盘点差异自动生成调整单（P3）、实例批量退役命令、报表改版。

## Capabilities

### New Capabilities
- `inventory-item-basis`: 盘点明细以台账行为基准——生成/提交/回显全部按 分公司×品目 台账行，应盘数量=在库数量

### Modified Capabilities
- `asset-freeze-readonly`: 冻结视图使命完成，requirements 整体 REMOVE（Asset 物理退役）
- `ledger-single-source`: 台账页面升级为主视图——实例管理品目行实例下钻（状态计数 + 抽屉列表 + 补录/生平）；期初唯一入口=增量导入
- `sidebar-navigation`: 「资产明细」入口删除；「固定资产表」更名「实例档案」

## Impact

- 后端：`apps/assets`（models/serializers/filters/views/urls/admin、删 2 命令、改对账提示）、`apps/inventories`（models/views/serializers + 迁移）、`tests/`（18 文件）
- 迁移风险：Asset 表 DROP（数据已在字典/台账/单据承载，P1 验收零差异）；盘点项 FK 换列 + 存量解析（PG DML/DDL 分片）；盘点历史项解析不到的删除（计数输出）
- 前端：`views/AssetList.vue`、`views/assets/AssetCreatePage.vue`、`views/assets/AssetImportDialog.vue` 下线；`views/assets/AssetSummary.vue` 加下钻；`views/mobile/`（AssetSearch/AssetDetail/MobileScan/ScanAsset）改台账口径；路由/导航/`api/assets.ts`/types 清理
- 兼容性：`/api/assets/` 请求将 404（前端已全部切换）；盘点 API payload 的 asset 字段改 stock
