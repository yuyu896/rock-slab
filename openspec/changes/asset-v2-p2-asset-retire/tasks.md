## 1. 后端模型与迁移

- [x] 1.1 盘点模型改造：InventoryItem/InventoryCheck `asset` FK → `stock` FK（AssetStock，PROTECT/CASCADE 沿原语义），盘点项加 (task, stock) 唯一约束
- [x] 1.2 迁移-inventories（DDL/DML 分片）：加 stock 列 → 存量按 (任务分公司, 资产编号) 解析换挂、解析不到的盘点项及 check 删除并输出计数 → 删 asset 列
- [x] 1.3 迁移-assets：Asset DeleteModel（表 DROP）；删 AssetFilterSet/AssetSerializer/AssetViewSet/admin 注册与主路由
- [x] 1.4 期初工具退役：删 preview_ledger_migration / migrate_initial_ledger；check_ledger_consistency 未初始化提示改指台账增量导入

## 2. 后端视图与序列化

- [x] 2.1 inventories/views：生成明细从台账行出发（跳过三列全零行，expected=在库）；check 按 分公司×品目 解析台账行；导出/列表回显改 item 联查
- [x] 2.2 inventories/serializers：asset 字段改 stock，asset_code/asset_name 改 stock.item 联查输出（字段名沿用避免前端大改）

## 3. 后端测试改造

- [x] 3.1 test_asset_crud.py 退役（冻结行为测试对象消失）；test_ledger_migration_and_guard 的 TestInitialMigration 改造/删除，未初始化容忍用例适配
- [x] 3.2 test_inventories.py / test_inventory_concurrency.py 改台账造数；conftest Asset 造数 helper 清理
- [x] 3.3 其余 12 个引用 Asset 的测试文件清 import / 改造；pytest 全量绿

## 4. 前端

- [x] 4.1 AssetList.vue / AssetCreatePage.vue / AssetImportDialog.vue 下线；/assets/list 与 /assets/list/create 重定向 /assets/summary
- [x] 4.2 侧边栏：删「资产明细」，「资产汇总」→「资产台账」，「固定资产表」→「实例档案」
- [x] 4.3 台账页实例下钻：实例管理行各状态计数 + 抽屉实例列表（补录/生平入口）；复用实例 API
- [x] 4.4 api/assets.ts 删 Asset 段；types 清 Asset 类型；盘点页字段适配
- [x] 4.5 移动端 AssetSearch/AssetDetail/MobileScan/ScanAsset 改台账/实例口径
- [x] 4.6 npm run build + vitest 绿

## 5. 收尾

- [x] 5.1 全量回归（pytest + vitest + build）；makemigrations --check 无漂移
- [x] 5.2 设计书核对：第三刀未偏离（Asset 退役=决策 #4，导航合并=第八节）；示例走查（台账下钻看实例生平）
