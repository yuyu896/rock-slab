## Why

动态复现的通知路由三缺陷：① 采购/归还按**调出分公司**文本路由——Web 端采购只传调入方，调出侧恒为空字符串 → branch 解析 None → `_users_with_operation_access` 走「为空时全量候选」分支，**全系统广播**（无关分公司经理也收到待审批通知）；模型早有正确口径 `业务分公司`（purchase/return→to_branch，其余→from_branch）但信号未用。② 采购审批落「已入库」，pre_save 信号只识别「已通过」→ 创建人 **0 条**审批结果通知、行政经理 **0 条**抄送，整链路静默。③ 创建人定位按**姓名字符串** `.first()` 找人——重名通知错人/漏人，现成的 `created_by` 外键闲置。

## What Changes

- 待审批/抄送通知的路由口径改用 `instance.业务分公司`（采购/归还=调入方，领用/调拨/回收=调出方）
- `_users_with_operation_access` 的分公司为空分支收敛：从「全量候选（广播）」改为「仅 admin+全部数据授权者」——分公司未知时只有全量范围者确定覆盖，杜绝广播
- 审批结果识别：`已通过` 或 `已入库` 均按审批通过处理（通知创建人+抄送照常触发）
- 创建人定位：优先 `created_by` 外键，FK 为空的存量单据回退姓名匹配；自通知排除改为 id 比较（姓名比较兜底）
- 移动端采购等已传调出分公司的路径行为不变（业务分公司对其同样成立）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `notification-data-scoping`: 「通知收件人必须按数据范围授权收敛」要求补齐：路由分公司口径=业务分公司、空分公司不广播、审批结果状态含已入库、创建人经 created_by 定位

## Impact

- `backend/apps/notifications/signals.py`：路由口径、空分支、状态识别、创建人定位四点
- `backend/tests/test_notification_routing.py`：新增广播消失/结果通知/重名定位用例
- 行为变化：Web 采购待审批通知从全员广播收敛为调入方审批人；采购审批通过后创建人/抄送方收到通知（原静默）
- 无迁移、无前端改动
