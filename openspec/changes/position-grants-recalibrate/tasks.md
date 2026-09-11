## 1. 模板变更

- [x] 1.1 `positions.py`：director 8→10 项（去 manage_dictionary，补 view_audit/manage_instances/dispose_assets）；leader 空→8 项
- [x] 1.2 测试同步：岗位目录接口断言 director 10 / leader 8；组长种子测试改模板集合断言（`test_apply_leader_gets_branch_scope_and_ops`）

## 2. 测试与验证

- [x] 2.1 后端 pytest 全绿：635 passed / 1 skipped / 6 xfailed（岗位权限 33 passed）
- [x] 2.2 本地 `seed_position_grants --apply` 后 `check_seed_grants` 通过 ✓

## 3. 生产与收尾

- [x] 3.1 生产数据先行收敛：组长 14/14 精确 8 项、区负责人 4/4 精确 10 项（备份 rock_slab_full_backup_20260911_pre_ld_tune.sql）
- [x] 3.2 拆 feat + openspec 两 commit，push
- [x] 3.3 生产部署（跳 5.5 台账对账——测试期 23 处已知差异），复跑 `check_seed_grants` 转绿
