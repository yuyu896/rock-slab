## 1. 后端换号机制

- [x] 1.1 `TransferLineInstance` 加 `调拨前编号 = CharField(max_length=100, blank=True, default='')`，生成 AddField 迁移并本地应用
- [x] 1.2 `instances.py` apply_line_instances 调拨分支：同事务内 `_next_seq(item, to_branch)` 取号 → `renumber_instance` 换号 → 写行实例关联的调拨前编号（驳回/草稿路径天然不触发）
- [x] 1.3 `serializers.py` get_instances 输出前编号（`{id, code, 调拨前编号}`，无值不输出或空串按现有惯例）
- [x] 1.4 新管理命令 `renumber_transfer_instances`：扫「编号分公司段 ≠ branch.code 且有生效调拨流水」实例，预览/`--confirm`，按 1.2 同规则换号+回写前编号，幂等跳过已处理项

## 2. 前端双编号展示

- [x] 2.1 调拨详情实例编号：有前编号显示「前编号 → 当前编号」（核实 PC 详情实例渲染点：TransferLinesEditor 只读态 / TransferDetailLayout；移动端审批详情有现成实例列则顺带，无则不动）
- [x] 2.2 types/index.ts 明细行 instances 类型补前编号字段

## 3. 测试与门禁

- [x] 3.1 后端测试：审批通过换号（计数器前移+前编号快照+branch 过户同事务）；驳回不换号；调回取新号；领用/归还/回收单实例编号不受影响；命令预览/确认/幂等三态
- [x] 3.2 架构测试：命令白名单登记（同 normalize_* 先例）
- [x] 3.3 门禁：后端 pytest 全绿（含对账）、前端 vitest 全绿、`npm run build` 通过

## 4. 收口

- [x] 4.1 拆两 commit（feat + openspec）并 push，等用户本地手验后自行部署
- [x] 4.2 部署项：AddField 迁移随 deploy.sh；上线后生产跑 `renumber_transfer_instances`（先预览核对 A-a00007-NB018-18/81 → NB032-102/103，再 --confirm）；对账零差异复核；提醒 32 分按调拨单新号重打 2 张标签
