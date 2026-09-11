# 实例编号按分公司 + 领用单台 — 技术设计

## Context

发号现状：InstanceSequence（item OneToOne，品目全局一行）锁行自增，编号 `{品目}-{全局序号}`；生产全局序号已至 1228。金华二分存量 75 台为全局大号（如 A-a00007-792）。领用行实例多选（一行可勾多台对应一个使用人）。

## Goals / Non-Goals

**Goals:** 编号 `{品目}-{分公司code}-{分公司内序号}`（每分公司每品目独立起号）；存量重编号命令；领用行单台选择。

**Non-Goals:** 调拨/归还/回收选择形态；编号展示/扫码/导出（字符串键不变）；调拨后实例改属分公司是否改号（不改——编号出生定终身，归属看 branch 字段与展示）。

## Decisions

### D1：序列矩阵化（item×branch）与发号格式

`InstanceSequence.item` 由 OneToOne 改 FK + `UniqueConstraint(item, branch)`（branch FK 非空——旧全局行删除，迁移：先删旧数据（可重算）或给旧行 branch 置空？直接**清空旧序列行**（重编号命令按存量重建各行计数），加 branch 列（non-null）+ 联合唯一。`_next_seq(item, branch)` 锁行；`generate_instances` 编号 `f'{item.asset_code}-{branch.code}-{seq}'`。分公司无 code 的历史节点（轮空已删）不构成问题。

### D2：重编号命令 renumber_instances（预览/--confirm）

按分公司×品目分组，组内按旧编号数值序排 N=1..k，逐台 UPDATE `内部编号`；同步 upsert InstanceSequence(branch,item,last_no=k)。幂等：编号已全符合新格式且序列一致则输出无需重编号。更新台账镜像无涉（不动数量）。审计：普通 UPDATE 不走单据——属一次性数据迁移（同 purge/归一先例），命令内打印明细留痕。

### D3：领用行单台（前端）

`InstancePicker` 加 `single?: boolean` prop：候选行点击即 `emit(['id'])`（单元素数组）并收起面板；勾选框变 radio 视觉（label 圆点）或直接行选高亮。`TransferLinesEditor` 在 `type==='assign'` 时传 single；`onInstancesChange` 领用行数量恒置 1。后端矩阵（len(instances)==数量）天然满足。

## Risks / Trade-offs

- [并发采购跨分公司同品目] — 序列行按 (item,branch) 锁行，互不阻塞
- [重编号后旧标签失效] — 已知代价（用户拍板重编），执行后需重打标签
- [同 code 分公司] — code 唯一性由组织模块既有约束承担

## Migration Plan

migration（InstanceSequence 结构）随部署；上线后跑 `renumber_instances`（预览→确认）。回滚：代码回退即可（编号字符串兼容任何格式，序列表新结构旧代码不读）。

## Open Questions

（无）
