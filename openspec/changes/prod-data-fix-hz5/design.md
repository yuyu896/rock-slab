# design — 5分杭州资产整清（合体形态再适用 + 不推送执行通道）

## Context

数据形态与 prod-data-fix-hz2（2分杭州）完全同型：1 张纯实例采购单（CG20260915-017，手机 67 + 一体机 60，镜像零差异）+ 45 张建账调整单（44 行非实例台账，数量 339 + 耗材 1718）。员工 1 人。

本单特殊约束：本地仓库有用户进行中的未推送改动（标签打印/员工归属等），**禁止 git push**。

## Decisions

### D1. 逻辑复用 hz2 合体命令

常量换为 5分杭州，其余逐行沿用（前置断言、单事务两侧、实时算量回退、成对删除、全零残行清理、内嵌对账复验、幂等）。

### D2. 不推送的执行通道

本地照常完成 openspec 工件 + 命令 + 测试 + 本地 commit（**不 push**，用户后续自行推送）；命令文件单独 scp 到服务器 `/root/`，执行时以卷挂载注入临时容器：

```
docker compose run --rm -v /root/prod_data_fix_hz5.py:/app/apps/assets/management/commands/prod_data_fix_hz5.py:ro \
  backend python -X utf8 manage.py prod_data_fix_hz5 [--apply]
```

镜像内已含 0914/0915 依赖模块（此前批次已部署），import 链完整；服务器仓库工作树零污染，`--rm` 容器即弃。审计链以本地 commit + 本 design 记录为准。

## Risks / Trade-offs

- [命令文件与仓库版本漂移] → 本单命令仅依赖已稳定部署的助手模块；后续用户 push + 常规部署后，仓库内文件与执行版一致
- [挂载路径笔误] → dry-run 先行验证 import 与断言全通过才 `--apply`

## Migration Plan

本地测试全绿 → 本地 commit（不 push）→ scp → 挂载 dry-run 复核 → 备份 → `--apply` → 独立对账 + 抽查 → 幂等复证。回滚走备份整库还原。

## Open Questions

（无）
