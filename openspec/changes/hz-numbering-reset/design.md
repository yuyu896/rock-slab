# 杭州编号归零 + 改名排查 — 技术设计

## Context

杭州序列污染（41/47 基础 + 88 台新实例从 42/48 发号）；09-15 03:15 Branch 变更（改名表操作）与 11:16 清理错位。代码层 renumber_instances 已具备所需能力（预览/--confirm/幂等/序列同步）。

## Decisions

### D1：直接复用 renumber_instances（无代码改动）

杭州 88 台：预览 → --confirm。命令按 (Length,编号) 排序重排——现存实例本就 42..82/48..94 连续，重排后恰为 1..41/1..47，序列同步为 41/47。之后新发号从 -42/-48 正常连续。

### D2：改名影响面排查（只读脚本）

列出 09-15 全天 `updated_at` 变动的 Branch，逐一核对：实例数 vs 序列 last_no、实例分公司与单据 to/from 是否自洽、台账镜像（check_ledger_consistency 兜底）。差异清单回报用户拍板处置（不做自动修复）。

### D3：守则落档

本提案 docs + 既有 MAINTENANCE 习惯：改名后体检（对账 + 序列抽查）。

## Risks / Trade-offs

- [重编后杭州标签需重打] —— 已知代价（88 台）
- [其他公司存在同类污染] —— 排查清单化处置，D2 覆盖

## Migration Plan

纯运维：备份 → 杭州 renumber → 对账 → 排查清单。

## Open Questions

（无）
