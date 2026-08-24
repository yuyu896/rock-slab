# 任务清单：流转单明细行化

## 1. 后端模型与迁移

- [x] 1.1 新增 `TransferLine` 模型（transfer FK CASCADE / item FK PROTECT / 行号 / 数量 / 本批规格 / 单价 / 金额 / 使用人 / department FK / 存放位置 / 固定资产内部编号），related_name='lines'，行号默认按创建顺序赋值
- [x] 1.2 新增 `DocumentSequence` 模型（type, date, last_no，唯一约束 (type, date)）与单据编号生成函数（select_for_update 锁行自增，前缀 CG/LY/GH/DB/HS）
- [x] 1.3 `Transfer` 新增 `单据编号` 字段（唯一，迁移回填）
- [x] 1.4 迁移 0002（atomic=False）：建表 + 逐张历史单据回填 1 条明细行（未登记编号自动建字典存根：单位"件"、类目"未分类"）+ 回填单据编号
- [x] 1.5 迁移 0003：删除单头平铺列（资产编号/资产名称/规格型号/调拨数量/单价/总金额/单位/资产类目/物品分类/存放位置/固定资产内部编号）
- [x] 1.6 新增 `preview_doc_line_migration` 命令：列出未登记编号清单与影响单据数
- [x] 1.7 在开发库（含存量数据）跑迁移，迁移前后各跑一次 `check_ledger_consistency`，确认均零差异

## 2. 后端服务与 API

- [x] 2.1 重构 `ledger.apply_document`：收集全部 (branch, item) 排序预锁 → 按行号逐行执行联动矩阵；任一行不足抛 LEDGER_INSUFFICIENT（错误信息带行号与品目定位）
- [x] 2.2 `TransferLineSerializer`：嵌套输出 + 品目字典回显（编号/名称/规格/单位/类目/管理方式），输入接受 item uuid
- [x] 2.3 `TransferSerializer` 改造：单头字段 + 嵌套 lines；删除已废弃平铺字段
- [x] 2.4 `TransferActionSerializer` 改造：接受 `{...单头, items: [...]}`；items 非空、数量 ≥1、item 必须为字典已登记品目（未登记提示相近编号）
- [x] 2.5 `_create_action` 改造：items 落库（行号顺序赋值）、单据编号生成、draft/immediate 语义保持（immediate 回收按行内部编号删 FixedAsset 的 P1 过渡行为不变）
- [x] 2.6 `perform_update`：已驳回编辑接受 items 整体替换（原子重写、行号重排）
- [x] 2.7 `perform_destroy`：拒绝删除 已通过/已入库 单据
- [x] 2.8 筛选与搜索：assetCode/关键字改为联查明细行

## 3. 消费方按行取数

- [x] 3.1 `check_ledger_consistency`：流水重算改为按明细行累计（prefetch lines__item）
- [x] 3.2 报表 `apps/reports/views.py`：数量/金额聚合改 TransferLine 联查，明细列表一行明细一行输出，resolve_user_scope 过滤不动
- [x] 3.3 通知 `apps/notifications/signals.py`：payload 改摘要（首行品目 + 等 N 项 + 合计数量）
- [x] 3.4 导入 `import_excel`：一行=单头+1 明细行（品目按编号解析 FK，单价/总金额/存放位置落行），校验与错误格式不变
- [x] 3.5 导出 `export_excel`：按明细行展开输出（单头信息随行重复，单位/类目联字典），模板列不变

## 4. 后端测试

- [x] 4.1 多明细单据全链路用例：创建（多行）→ 审批 → 台账逐行联动 → 详情/列表输出形状
- [x] 4.2 部分行不足整单回滚用例（一张单两行，一行充足一行不足 → 全回滚）
- [x] 4.3 并发用例：两张多行单据相反品目顺序同时审批不死锁；并发创建单据编号不重复
- [x] 4.4 已生效单据禁删、驳回编辑 items 整替、items 空拒收、未登记品目拒收（含相近编号提示）用例
- [x] 4.5 存量迁移用例：平铺单据迁移后明细行内容正确、未登记编号入籍存根、迁移后对账零差异
- [x] 4.6 既有 transfers/ledger/report/notification 用例改造为明细行口径，全量 pytest 绿
- [x] 4.7 架构测试（services 之外无台账写）保持通过，唯一写入口未放松

## 5. 前端类型与 API 层

- [x] 5.1 `types`：新增 `TransferLine`（含字典回显字段）与 `TransferDocument`（单头+lines），替换旧扁平 `Transfer` 的使用方；`TRANSFER_TYPES` 从 useTransferList 移入 constants 并对齐 action 枚举
- [x] 5.2 `api/transfers.ts`：五个创建函数改 `{...单头, items}` payload；`useAssetCodeAutofill` 退役删除
- [x] 5.3 移动端提交适配：MobileAssign / MobileTransfer 改 items payload（经 lookupCategoryByCode 解析品目 uuid）

## 6. 前端组件与页面

- [x] 6.1 `ItemPicker` 组件：品目字典远程搜索点选（编号/名称检索，回显规格/类目/管理方式）
- [x] 6.2 `TransferLinesEditor` 组件：可增删行表格 + 类型专属列（采购单价/金额、领用使用人/部门、回收存放位置/内部编号、调拨本批规格）
- [x] 6.3 四个创建页（Purchase/Assign/Transfer/Recovery）改造：单头表单 + TransferLinesEditor；AssignCreate 从逐行 N 请求改为一次提交一张多行单
- [x] 6.4 四个详情页统一"一行元信息 + 明细表"；新增回收 `:id` 详情页，列表弹窗退役
- [x] 6.5 四个列表页改单头粒度列（单号/日期/分公司/品项数/总数量/状态/操作），assetCode 筛选与搜索联行
- [x] 6.6 旧版采购页清退：删 `views/Purchase.vue`、`purchases/PurchaseCreateForm.vue`，`/assets/purchase` 重定向 `/transfers/purchase`（导入弹窗能力保留在采购列表页）
- [x] 6.7 其他消费方回归：Dashboard、AssetList（按品目关联单据联行）、移动端 Approval 页
- [x] 6.8 `useTransferList` 适配单头粒度列表与摘要统计

## 7. 前端测试与验收

- [x] 7.1 vitest：ItemPicker 点选、TransferLinesEditor 增删行与校验、创建页 payload 形状（一次请求多行）、列表单头列
- [x] 7.2 `npm run build` 类型检查通过、`npm run test` 全绿
- [x] 7.3 手工走查：一张多行采购单从创建到审批到台账联动到导出的完整链路（开发环境双端）
