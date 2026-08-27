## 1. 后端：模型与迁移

- [x] 1.1 `InventoryTask` 增 `stock_bin`（stock/recycle，默认 stock）与 `department`（nullable FK organizations.Department）；新增 `InventoryInstanceItem`（task FK、instance FK、result、check_count、checked_by/at、remarks；unique(task, instance)）；生成纯 DDL migration
- [x] 1.2 serializer：任务增 stock_bin/department/`inventoryKind`（'stock'|'instance'）输出；创建校验 department∈branch、实例盘忽略 stock_bin；新增 InventoryInstanceItemSerializer

## 2. 后端：库别维度（台账盘）

- [x] 2.1 `_generate_items`：行集 = 目标库别列 > 0（类目过滤保留），expected = 对应列
- [x] 2.2 `check` 动作 expected 与 `generate_variance_adjustments` 目标列按 task.stock_bin 参数化（services 目标列跟库别，事由文案含库别名）
- [x] 2.3 报告/导出基本信息增库别

## 3. 后端：部门实例盘

- [x] 3.1 `start` 对实例盘任务生成实例快照清单（branch×department×在用，类目可选过滤）
- [x] 3.2 新增 `check-instance` 动作：{instanceId, found, remarks} → matched/missing（重复核对后者为准，check_count 累计）；任务内实例校验
- [x] 3.3 `submit` 漏盘规则作用于实例项（zero→missing，keep→unchecked）；`recount` reset 覆盖实例项
- [x] 3.4 `approve` 实例盘不生成调整单；progress/report 按实例口径（应到/实到/缺失/未核对）
- [x] 3.5 导出：实例盘明细 sheet（按使用人分组、内部编号粒度、缺失标待跟进）+ 汇总；调整单段"无（实例盘不改账）"
- [x] 3.6 报告接口输出缺失实例清单（供前端一键回收预填：品目聚合 + instances）

## 4. 前端

- [x] 4.1 `constants`：库别选项（在库/回收库）与盘点方式选项；`types`/`api`：任务新字段、checkInventoryInstance、报告实例口径类型
- [x] 4.2 创建页：台账/实例方式切换（库别 vs 部门显隐、部门按分公司过滤）、实例盘说明文案、重复规则场景提示
- [x] 4.3 详情页（Inventory.vue）：实例盘按使用人分组清单（逐台已找到/未找到 + 备注）、扫码/输入内部编号打钩、进度按台；台账盘显示库别
- [x] 4.4 报告视图：实例盘汇总（应到/实到/缺失）+ 缺失明细 + "对盘亏项发起回收单"按钮（携带 taskId 跳转回收创建页）
- [x] 4.5 RecoveryCreate：支持 query 预填（taskId → 拉缺失实例预填明细行与调出分公司）
- [x] 4.6 MobileScan：实例盘任务扫码/输入内部编号打钩（found=true）

## 5. 测试与验证

- [x] 5.1 后端 pytest：回收库盘全链路（生成按回收库列、差异修回收库列、负数回滚）、实例盘全链路（生成快照、核对、漏盘规则、审批零调整单零改账、部门归属校验、数量品目不出清单）
- [x] 5.2 前端 `npm run build` + vitest
- [x] 5.3 浏览器实测：创建两种任务、实例盘分组打钩、报告缺失明细与一键回收预填

## 6. 收尾

- [x] 6.1 v2-revision-draft.md §八 第 6 案状态改 ✅；feat + openspec 两 commit → push → 归档
