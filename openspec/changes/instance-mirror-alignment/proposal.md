# 提案：实例镜像警告去重与管理方式切换对齐（P2 第二刀补丁）

## Why

P2 第二刀上线部署暴露两个缺口：一、对账命令的「数量管理品目挂实例」警告按实例重复打印（同一品目刷屏几十行，生产 400+ 行警告淹没关键信息）——根因是模型默认排序 `ordering=['内部编号']` 把排序列混入 SELECT/GROUP BY，`DISTINCT` 与聚合双双失效（聚合 bug 此前被累加循环掩盖）；二、设计书十一节「决断路径」缺失落地工具：管理员把品目从数量管理改为实例管理后，实例镜像立即开始执法且必然与数量管理时代的台账不符，下一次部署会被对账闸门拦住——迁移 0019 的对齐只在迁移时执行一次且当时按设计跳过数量管理品目，需要可重复执行的对齐命令。

## What Changes

- 修复：对账命令实例聚合与警告去重查询补 `.order_by()`（清模型默认排序），警告改为按品目一行并携带实例条数
- 新增 `align_ledger_to_instances` 管理命令：预览（默认）/`--confirm` 两段式；对实例管理品目 × 分公司，台账三列对齐实例计数（退役除外），经台账唯一写入口生成非期初调整单（事由「管理方式切换对齐」）；幂等可重复执行；branch 为空实例跳过并警告

## Capabilities

### New Capabilities
（无）

### Modified Capabilities
- `ledger-consistency-guard`: 对账命令警告按品目去重（一行一品目带条数）；新增「管理方式切换对齐命令」requirement（预览/确认、唯一写入口、幂等）

## Impact

- 后端：`apps/assets/management/commands/check_ledger_consistency.py`（两处 `.order_by()` + 警告文案）、新增 `commands/align_ledger_to_instances.py`
- 测试：`tests/test_instance_binding.py` 新增警告去重与对齐命令流程用例（切换→对账失败→预览→确认→对账通过→幂等）
- 运维：生产约 20 个品目、数百实例的「数量管理挂实例」存量决断后，用新命令对齐；部署流程不变
