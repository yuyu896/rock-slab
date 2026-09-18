## Why

33分宁波 3 个一体机实例（A-a00011-NB033-35/43/72）系错误登记，用户要求点删（2026-09-18 第二批）。实测：三台分属三张多实例行出生单（CG20250227-004 行1 ×7、CG20250210-004 行1 ×7、CG20250205-004 行1 ×22），全在库、仅出生链、镜像 72=72——与前案 prod-data-fix-nb33（09-15 点删 -16/-17/-19）完全同型。

## What Changes

- 新增一次性纠错命令 `prod_data_fix_nb33_2`（默认 dry-run，`--apply` 执行，单事务）：按内部编号点删 3 实例，各出生行数量 −1（7→6、7→6、22→21），台账在库 72→69；发号序列保留。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

（无——「按内部编号点删实例」要求的再次适用）

## Impact

- **后端**: `backend/apps/assets/management/commands/prod_data_fix_nb33_2.py`（派生自 nb33）+ `backend/tests/test_prod_data_fix_nb33_2.py`
- **生产数据**: 3 实例删除、3 行数量各 −1、A-a00011 台账在库 72→69；他分公司与同品目其余 69 台零波及
