## Why

2026-09-11 生产已完成分公司行政（manager）操作授权收紧：113 人精确收敛为 6 项（管理资产、审计日志、抄送记录、统计报表、管实例、资产处置），收掉审批/建号/字典/台账调整等 5 项（审批流上收组长/区负责人/管理员）。但代码岗位模板仍是 8 项口径，`check_seed_grants` 门禁对 manager 抽样按旧模板校验已 FAIL（exit 1），下次 `deploy.sh` 会被拦截。

## What Changes

- 岗位模板 `POSITION_TEMPLATES['manager'].operations` 从 8 项改为 6 项：`manage_assets` / `view_audit` / `view_all_notifications` / `view_reports` / `manage_instances` / `dispose_assets`
- 移除模板中的 `manage_users` / `manage_dictionary` / `approve_transfer` / `approve_inventory` / `adjust_ledger`
- 同步更新测试断言（`test_position_permissions` 等引用 manager 模板 8 项处）
- **BREAKING**（口径层面）：此后新建分公司行政账号，权限分配页预填勾选为 6 项；已有账号存量授权不追溯（生产已于数据层完成收敛，两者一致）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `position-appointment-permissions`: 「岗位模板」需求中 manager 预填操作码清单由 8 项变更为 6 项（管理资产/审计日志/抄送记录/统计报表/管实例/资产处置），分配页预填场景与门禁校验口径随之变更

## Impact

- `backend/apps/permissions/positions.py`（模板注册表，1 处清单修改）
- `backend/tests/test_position_permissions.py` 及其他断言 manager 模板清单的测试
- `check_seed_grants` / `seed_position_grants` 命令动态读模板，无需改码，口径自动跟随
- 前端权限分配页预填来自后端接口（岗位目录），无前端改动
- 生产数据已先行收敛（113/113 精确 6 项，备份 `rock_slab_full_backup_20260911_pre_manager_tighten.sql`），本变更使代码追平数据，门禁转绿
