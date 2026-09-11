# 实例编号按分公司 + 领用单台 — 实施任务

## 1. 后端：序列矩阵与发号

- [x] 1.1 `InstanceSequence`：item OneToOne→FK + branch FK(非空) + (item, branch) 唯一；迁移清空旧全局行
- [x] 1.2 `_next_seq(item, branch)` 与 `generate_instances`：新格式 `{品目}-{branch.code}-{序}`；同分公司品目连续/跨分公司独立起号测试
- [x] 1.3 `renumber_instances` 命令：分组重排（预览/--confirm/幂等）+ 测试（重编后编号格式、序列同步、关联保留）

## 2. 前端：领用单台

- [x] 2.1 `InstancePicker` 加 `single` prop：点选即定（单元素）并收起；样式行选高亮
- [x] 2.2 `TransferLinesEditor`：assign 行传 single、数量恒 1；调拨/归还/回收不变
- [x] 2.3 vitest：领用行单台（换选非追加）、数量恒 1；调拨行多选不回归

## 3. 验证与收尾

- [x] 3.1 全量 pytest + `npm run build` + vitest 全绿
- [x] 3.2 本地手验：采购生成新格式编号（分公司独立起号）；领用单台流；重编号命令演练
- [ ] 3.3 生产部署 + `renumber_instances`（金华 75 台）+ 对账验证（待部署时勾）
