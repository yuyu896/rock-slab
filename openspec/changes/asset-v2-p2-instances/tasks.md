## 1. 后端模型与迁移

- [x] 1.1 FixedAsset 重塑：新增 item FK（PROTECT）、birth_line FK（PROTECT，可空）、department FK（可空）、状态枚举改 在库/在用/回收库/退役；删除手抄品目文本列与 数量/出库日期；保留 内部编号/序列号/使用人/branch/入库日期/备注
- [x] 1.2 新增 InstanceSequence 模型（品目一行，锁行自增发号）与行-实例关联 through 模型 TransferLineInstance（unique(line, instance)），TransferLine.instances M2M；TransferLine 删除 固定资产内部编号 列
- [x] 1.3 Transfer 单头新增 领用来源（stock 默认 / recycle_bin）
- [x] 1.4 迁移-step1（atomic=False 拆 DDL/DML）：加列 + item 按存量资产编号回填；编号不在字典者自动创建字典存根（management_type=instance，名称取实例手抄名）；空闲→回收库状态映射
- [x] 1.5 迁移-step2（atomic=False）：回收类历史单据行按 固定资产内部编号 文本回链存活实例；供应商/单价/购入金额有值者折叠进备注前缀；删除手抄列与 TransferLine.固定资产内部编号；InstanceSequence 按存量最大序号纯 Python 初始化
- [x] 1.6 迁移-step3：实例管理品目 × 分公司 台账列 vs 实例计数差异生成期初调整单（is_initial，经 ledger.apply_adjustment）；branch 为空实例跳过并输出警告清单
- [x] 1.7 本地跑迁移（SQLite）+ `check_ledger_consistency` 验证存量路径零差异

## 2. 后端服务层

- [x] 2.1 新建 apps/assets/services/instances.py：`generate_instances(line, branch)`（锁 InstanceSequence 发号、birth_line、状态在库）与 `transition_instances(transfer, line, locked)`（领用/归还/调拨/回收矩阵迁移，含清空/写入使用人与部门）
- [x] 2.2 ledger.apply_document 扩展：数量变动同事务内逐行调用实例生成/迁移；实例 select_for_update 终检（状态/分公司/品目/数量一致，按输入矩阵），失败整单回滚带行号定位；领用矩阵按 领用来源 扣 在库/回收库 列
- [x] 2.3 transfers/views.py `_apply_ledger`：删除按文本内部编号物理删 FixedAsset 的 P1 过渡逻辑（退役取代）

## 3. 后端 API

- [x] 3.1 TransferLineInputSerializer 加 instances（uuid 数组，默认 []）+ 创建/编辑两处校验输入矩阵（品目管理方式 × 类型、len==数量、状态/分公司预检、领用行使用人必填、领用来源字段）
- [x] 3.2 TransferLineSerializer 输出实例列（内部编号列表）；TransferSerializer 输出 领用来源
- [x] 3.3 FixedAssetViewSet 重塑：list/retrieve/export 保留（联字典 + 出生行派生输出）；create/update/destroy/batch-delete/import 全部 405/410 冻结；新增 supplement action（序列号/备注，manage_instances）；新增 timeline action（生平=档案+出生行派生+关联行倒序）
- [x] 3.4 FixedAssetFilterSet：状态/分公司/品目关键字/待补录 筛选
- [x] 3.5 check_ledger_consistency 扩展实例不变量（实例管理品目各状态计数==台账列；数量管理品目挂实例输出警告不改退出码）

## 4. 后端测试

- [x] 4.1 test_fixed_asset.py 重写：四态状态机、冻结端点（405/410）、补录端点权限与字段限制、timeline 生平、待补录筛选
- [x] 4.2 test_transfer_lines.py 扩展：instances 输入矩阵全场景（必带/禁带/数量不符/状态不符/来源不符）、驳回编辑整替携带实例
- [x] 4.3 test_ledger_contract.py 扩展：五单实例迁移矩阵场景、生效终检（并发占用回滚）、领用回收库来源扣列、回收直接处置退役不删
- [x] 4.4 test_ledger_migration_and_guard.py 扩展：实例不变量检出差异、迁移对齐期初调整单、编号存根入籍
- [x] 4.5 test_ledger_architecture.py 扩展：FixedAsset/TransferLineInstance 写操作白名单仅 services（视图越权写即红）
- [x] 4.6 pytest 全量回归绿

## 5. 前端

- [x] 5.1 api/types：fixed-assets API 更新（新列字段、supplement/timeline）、transfers 加 领用来源 与行 instances；constants 加 领用来源标签
- [x] 5.2 FixedAssetList.vue 重做：新列布局、待补录标识与筛选、补录弹窗（仅序列号/备注）、生平抽屉（出生信息+关联单据行倒序）、移除新增/导入/编辑/删除入口
- [x] 5.3 FixedAssetCreate.vue 下线：删页面/路由/导航入口
- [x] 5.4 实例点选组件（InstancePicker）：按 分公司×品目×状态 拉可选实例、勾选数与行数量联动
- [x] 5.5 AssignCreate.vue：领用来源单选；实例管理行内嵌 InstancePicker（按来源切状态）；归还/调拨/回收创建页接入对应状态选择器
- [x] 5.6 单据详情页（五类型 TransferDetailLayout/TransferLinesTable）：实例列展示内部编号并可跳转生平；回收行去掉文本内部编号列
- [x] 5.7 移动端：即时回收改为实例引用（如有文本内部编号路径一并改）
- [x] 5.8 npm run build + vitest 绿

## 6. 收尾

- [x] 6.1 设计书核对：本刀未偏离 docs/design/asset-model-v2.md（偏离即先修宪）；P2 路线表勾进度
- [x] 6.2 手动走查示例：一台笔记本的一生（采购生成→补录→领用→归还→调拨→回收退役）全程无阻
- [x] 6.3 部署预案复查：deploy.sh 对账闸门将执行双不变量；PG 迁移 atomic=False 分片就位
