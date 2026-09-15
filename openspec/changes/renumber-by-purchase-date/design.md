# 重编号按日期 — 技术设计

## Context

renumber_instances 现按 `_old_sort_key`（旧编号尾段数字）排序。发号按生效序，历史导入乱序导致编号≠时间序。

## Decisions

### D1：排序键可切换

`--by-date`：分组排序键改为 `(出生采购日期 or 入库日期 or date.max, 旧编号尾段数字)`——日期为主、旧号为稳定次键（同日按原序，避免同日抖动）。日期来源：`inst.birth_line.transfer.调拨日期`（select_related 已有链）。

### D2：其余逻辑不动

分组/预览/幂等/序列同步复用现有实现；输出加「重编后请重打标签」提示（两种模式统一）。

## Risks / Trade-offs

- [重编改号影响已贴标签] —— 命令输出明示；按需执行
- [同日多批相对顺序] —— 次键旧号保持稳定

## Migration Plan

纯命令增强，随部署生效。

## Open Questions

（无）
