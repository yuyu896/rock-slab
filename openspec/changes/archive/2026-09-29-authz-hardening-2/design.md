# 权限加固第二批 — 技术设计

## Context

缺陷排查中低危项清单及拍板结论（2026-09-29）：盘点写接口零码（挂 manage_assets）；流转单无归属（仅创建人+admin）；warehouse 死配置；改用户分公司不校验目标值；branch=None 实例穿过写校验；前端权限会话延迟。调拨单边问题另立 transfer-reject-channel。

## Goals / Non-Goals

**Goals:** 盘点写动作全部有码可拦；他人单据不可改删（创建人/admin 除外）；杂项清零。

**Non-Goals:** 不新增操作码/不动模板与种子门禁；不动调拨单边校验（另变更）；不做单据转移（改归属人）功能。

## Decisions

### D1：盘点挂码沿用类级 `required_operations` 字典

[inventories/views.py:36](../../backend/apps/inventories/views.py) 的类级字典补齐写动作 → `manage_assets`；approve/reject 已显式 `permission_classes=[OperationPermission]` 且字典值 `approve_inventory`，维持。GET 类（detail/report/export-template/import-template）登录可读不动。
理由：与 import_excel/approve 现有机制同构，零新概念；manager/leader 模板含 manage_assets，日常使用不受影响——被拦的只有"仅有任命、无码"的账户，正是要拦的。

### D2：流转单归属 = `created_by` 本人或 admin

新 helper `_assert_owner_or_admin(user, transfer)`，挂 update/partial_update/destroy/submit/resubmit/withdraw。依据：`Transfer.created_by`（models.py:108）是权威创建人（`经办人` 是展示字符串，导入/代录也写 created_by=操作者）。approve/reject 不挂归属——审批权按 `approve_transfer` 码，审批人常非创建人；驳回后创建人仍可改可重提，流程闭环不断。
备选「同范围持码可操作」被用户否（选最严口径）；admin 豁免兜底协作场景（行政接手走 admin）。

### D3：孤儿实例在 batch-update 层拦，不动全局 validate

`validate_branches_in_scope` 对 None 的跳过被「可选无调入方」等调用方依赖（如非调拨单 to=None），全局收紧会误伤。故仅在 batch-update 循环里：`inst.branch is None` → errors「未归属分公司」。可见性（非 admin 看不到孤儿）维持现状——属数据卫生问题，实例本必有分公司。

### D4：用户管理校验「提交的目标分公司」

users 的 create/update 在 `_validate_in_scope`（现只看目标用户**现属**分公司）之外，追加校验 payload 中的 branch 新值在操作者范围（admin/全部数据豁免）。防"把人改挂到范围外分公司"的管理越界。

### D5：前端权限节流重拉

router.afterEach：距上次 `permissions/me` 拉取 ≥5 分钟则后台静默重拉（失败不打扰）。权限变更（授权/撤权/任命）最迟 5 分钟或下次刷新生效，会话延迟从"重登才生效"降为分钟级。

## Risks / Trade-offs

- [盘点历史调用方（若有定时/脚本无码调用）] → 系统内仅前端用户经 API，无脚本；上线后如有 403 报障即查该账户码。
- [归属收紧误伤既有协作] → admin 可操作全部单据兜底；上线观察期内报障走 admin 接手。
- [test_write_scope 引用 warehouse 死配置] → 同笔清理并改写该断言为存活动作。
- [路由 afterEach 增加请求] → 5 分钟节流，正常操作无感。

## Migration Plan

后端行为收紧随常规发版；无数据迁移。部署后验证：无码账户建盘点 403、manager 正常；他人单据改删 403、创建人正常。

## Open Questions

（无——四项拍板齐备：挂 manage_assets / 仅创建人+admin / 杂项全清 / 调拨另立。）
