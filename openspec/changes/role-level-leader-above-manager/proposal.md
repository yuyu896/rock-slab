# 职级修正——行政组长高于分公司行政

## Why

实际组织结构中行政组长（leader）管辖一个组（组下挂多家分公司），分公司行政（manager）管辖单家分公司，组长职级应更高。当前前端 ROLE_LEVELS 把 manager(L3) 排在 leader(L4) 之上，导致组织架构页人员排序中分公司行政排在行政组长前面，与组织事实相反。

## What Changes

- `ROLE_LEVELS` 互换：admin:1 > director:2 > **leader:3（行政组长）** > **manager:4（分公司行政）** > supervisor:5 > staff:6（退役岗保持队尾）
- 组织架构页排序断言更新（行政组长排在分公司行政前）
- 非目标：操作授权、数据范围、审批逻辑零改动（均按授权码/任命驱动，不依赖等级——等级仅用于展示排序）；`hasMinRole`/`roleLevel` 死代码不清理（另案）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `personnel-management`: 职级展示序修正为 行政组长 > 分公司行政（组织架构人员排序口径）

## Impact

- **前端**: `constants/index.ts`（一行）、`tests/utils/orgTree.test.ts`（断言）
- 后端零改动
