## Why

2026-09-11 用户拍板岗位授权再校准：组长从 12 项全量收敛为 8 项（去除管理用户/管理组织架构/管理品目字典/台账调整单——建号与组织变动上收区负责人与管理员，调账收口），大区负责人定为 10 项（去除管理品目字典与台账调整单，其余全有——补齐审计/实例/处置）。生产数据已先行收敛（组长 14/14×8、区负责人 4/4×10），但代码 director 模板仍含 manage_dictionary，`check_seed_grants` 门禁 FAIL。

## What Changes

- 岗位模板 `POSITION_TEMPLATES`：
  - `director.operations` 8→10 项：去除 `manage_dictionary`，新增 `view_audit` / `manage_instances` / `dispose_assets`
  - `leader.operations` 空清单→8 项：`manage_assets` / `approve_transfer` / `approve_inventory` / `view_audit` / `view_all_notifications` / `view_reports` / `manage_instances` / `dispose_assets`（组长从"模板为空、特例授予"转为模板化标准）
- 同步测试：岗位目录接口断言 director 10 项/leader 8 项；组长种子测试由"无操作码"改为"模板 8 项补齐"
- **BREAKING**（口径层面）：此后新建组长号预填 8 项、区负责人号预填 10 项；品目字典与台账调整两权全系统仅 admin 可授特例持有

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `position-appointment-permissions`: 「岗位模板」需求中 director 预填清单 8→10 项、leader 由空模板改为 8 项标准清单，分配页预填与门禁抽样口径随之变更

## Impact

- `backend/apps/permissions/positions.py`（两处清单）
- `backend/tests/test_position_permissions.py`（目录断言、组长种子测试）
- `check_seed_grants` / `seed_position_grants` 动态读模板，口径自动跟随
- 生产数据已先行精确收敛（备份 `rock_slab_full_backup_20260911_pre_ld_tune.sql`），本变更使代码追平、门禁转绿
- 四岗终态：admin 全能（内置）/ director 10 / leader 8 / manager 6
