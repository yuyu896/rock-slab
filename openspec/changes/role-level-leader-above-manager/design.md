# 职级修正 leader > manager — 技术设计

## Context

ROLE_LEVELS 仅前端存在；真实消费方只有组织架构页的 sortEmployeesByRole（职级高在前）。后端权限走授权码、数据范围走任命展开，与等级无关。

## Goals / Non-Goals

**Goals:** 展示职级序对齐组织事实（组长 > 分公司行政）。

**Non-Goals:** 不动授权种子/数据范围/审批；不清理 hasMinRole、roleLevel 死代码。

## Decisions

### D1：仅互换常量序号

`leader: 3, manager: 4`（supervisor/staff 退役岗保持 5/6 队尾）。orgTree 测试的期望序同步更新。零运行时逻辑分支依赖序号差值，互换无涟漪。

## Risks / Trade-offs

（无——展示层一行常量；vitest 守护排序）

## Migration Plan

随前端构建生效；无数据、无回滚。

## Open Questions

（无）
