## 1. 品目字典（Category 升级）

- [ ] 1.1 Category 模型加字段：管理方式(quantity|instance,默认quantity)、规格(可空)、图片、是否租用(默认否)、默认供应商；迁移
- [ ] 1.2 下线 4 个反范式计数字段（asset_count/in_stock_count/asset_total_quantity/in_stock_quantity）与 categories/signals.py 计数信号；迁移；清理引用处
- [ ] 1.3 字典 serializer/view 适配新字段（lookup 端点带出管理方式/规格/默认供应商）；删除保护（被台账/单据引用时 PROTECT 报错提示）
- [ ] 1.4 字典管理接口权限挂 `manage_dictionary` 操作码；单据创建时编号在字典存在性校验 + 相近编号提示（difflib）
- [ ] 1.5 前端字典管理页：新字段列（管理方式/规格/租用/默认供应商）+ 分编号判定测试三问提示文案
- [ ] 1.6 后端测试：品目字段契约、唯一约束、删除保护、未登记编号拒绝（对应 item-dictionary spec 场景）

## 2. 台账结构重构（AssetStock）

- [ ] 2.1 AssetStock 重构：branch FK + item FK(→Category, PROTECT)、唯一约束(branch,item)、在库/在用/回收库三存储列、行级警戒线；删冗余文本列；结构迁移（数据迁移另见第 8 组）
- [ ] 2.2 serializer 联字典输出（编号/名称/规格/类目/物品分类/管理方式）+ 总量计算输出 + 充足判定（行级警戒线空则取字典默认，口径=在库）
- [ ] 2.3 台账列表接口筛选适配（分公司/类目/物品分类/关键词搜编号名称规格），数据隔离语义回归验证
- [ ] 2.4 台账直接新增/编辑/删除/批量删除接口下线（405），模板下载与导出保留
- [ ] 2.5 后端测试：行粒度唯一、四列语义、充足判定两口径、写接口 405（对应 ledger-single-source 与 asset-summary MODIFIED 场景）

## 3. 唯一写入口（ledger service）与调整单

- [ ] 3.1 新建 assets/services/ledger.py：apply_document（按单据类型分发矩阵）、apply_adjustment、get_or_create_row（select_for_update 行锁 + 充足性校验 + 派生列维护），全部事务化
- [ ] 3.2 LedgerAdjustment 模型（branch/item/目标列/变动量/事由/经办人/is_initial）；创建即生效、权限 `adjust_ledger`、负数拒绝；serializer/view/URL
- [ ] 3.3 后端测试：service 矩阵各路径、行锁并发（两单竞争不超卖）、调整单权限与负数拒绝（对应 document-ledger-sync spec 场景）

## 4. 五单对称联动（transfers 改造）

- [ ] 4.1 Transfer 模型加字段：回收去向(recycle_bin|dispose,默认recycle_bin)、处置方式(出售/报废/捐赠)、处置金额；迁移
- [ ] 4.2 五个 @action 与 approve 改造：删除 _sync_asset/_apply_warehouse_stock/_sync_assign/_sync_return/_sync_transfer 对 Asset 的全部写入；改调 ledger service（采购建行/领用校验充足/归还/调拨双边/回收二去向）
- [ ] 4.3 单据创建校验：领用/归还/调拨/回收必填字典内资产编号；分公司维度显式解析，移除字符串模糊匹配三级 fallback
- [ ] 4.4 流转批量导入适配：assign 模板补资产编号列；校验前置（编号在字典、分公司合法）
- [ ] 4.5 后端测试：五单矩阵端到端（审批→台账各列变动）、在库不足拒绝、immediate 回收二去向、批量导入（对应 document-ledger-sync 场景；更新 test_transfers/test_recovery_stock_link 中"非回收不写台账"的旧断言为对称联动断言）

## 5. Asset 冻结与下游切换

- [ ] 5.1 Asset ViewSet 写方法下线（405）、导入 action 下线（410 提示走台账导入）；GET/导出保留
- [ ] 5.2 盘点：移除 _adjust_inventory 对 Asset 数量的写操作，审核仅记录差异（含提示文案"P1 记录模式，修数走调整单"）；InventoryItem FK 与清单生成暂不动
- [ ] 5.3 报表切台账：overview/by_branch/by_status/by_category 改从 AssetStock 聚合（状态维度=三列），购入金额从采购单聚合；口径注释
- [ ] 5.4 后端测试：Asset 写接口 405/410、领用审批后 Asset 零变化、盘点审核不改数量、报表随台账联动（对应 asset-freeze-readonly 场景）
- [ ] 5.5 前端资产列表页只读化：移除新建/编辑/删除/批量删除/导入入口，页头加"历史视图（P2 退役）"标识

## 6. 台账导入改增量

- [ ] 6.1 后端：import_excel 重写为两段式——预览（比对现值出差异清单）+ 确认（每差异生成调整单，事由=导入调整）；模板改 分公司/资产编号/在库数量；未登记编号整行拒绝带相近提示
- [ ] 6.2 前端 SummaryImportDialog 改差异预览确认流；下线 SummaryFillDialog（从台账填入资产明细/固定资产）
- [ ] 6.3 后端测试：差异生成调整单、现值一致无差异跳过、未登记编号拒绝（对应 asset-summary MODIFIED 导入场景）

## 7. 部门字典

- [ ] 7.1 Department 模型（branch FK PROTECT + 名称，unique together）挂 organizations；serializer/view/URL + 按分公司 options 端点
- [ ] 7.2 前端：流转创建页（调出/调入/需求部门）与固定资产创建页部门输入接字典下拉（按所选分公司过滤，允许自由输入）；部门字典管理入口（组织页内或独立小页）
- [ ] 7.3 后端测试：唯一约束、跨分公司同名允许、options 过滤、权限（对应 department-dictionary 场景）

## 8. 存量迁移（期初调整单）

- [ ] 8.1 preview_ledger_migration 命令：未登记编号清单（带相近建议）、状态分桶统计、与旧 AssetStock 差异行、部门归一清单
- [ ] 8.2 migrate_initial_ledger 命令：纯 Python 按(branch,编号)聚合分桶（在库/使用中+维修中→在用/报废出局）→ 每行期初 LedgerAdjustment → service 入账；存在未登记编号时拒绝执行；部门归一生成字典行
- [ ] 8.3 后端测试：分桶规则、期初单生成后 check 零差异、未登记编号阻断、与旧台账差异以 Asset 聚合为准（对应 initial-ledger-migration 场景）

## 9. 机器执法与宪法

- [ ] 9.1 check_ledger_consistency 命令：逐行逐列比对（流水=期初单+其后已通过 Transfer+非期初调整单），差异表输出，exit 1
- [ ] 9.2 架构测试：扫描 backend/apps 源码断言台账数量写模式仅在 services/ledger.py、migrations、tests 白名单
- [ ] 9.3 deploy.sh 在 migrate 后追加 check_ledger_consistency，非零中止；DEPLOYMENT.md 补 P1 上线步骤（备份→部署→预览→迁移→对账→放行）
- [ ] 9.4 CLAUDE.md 增铁律节（两条铁律原文 + 提案审查两问）
- [ ] 9.5 后端测试：构造漂移场景断言对账检出；架构测试抓越权写的红/绿用例

## 10. 前端台账页与收尾

- [ ] 10.1 台账页改造：13 列（含管理方式/四列数量）、写按钮移除（保留导入导出）、不足红色标识、分页序号跨页累加保持
- [ ] 10.2 回收创建页：去向二选一 radio（入回收库/直接处置），直接处置时显示处置方式+金额
- [ ] 10.3 全量回归：后端 pytest 全绿；前端 npm run test 与 build 通过；对账命令全库零差异演练（开发库）
