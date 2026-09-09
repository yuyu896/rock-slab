# 岗位授权批量种子——2026-09-08 建号导入补授，解锁被拦部署

## Why

2026-09-08 批量建号（134 账号）只建了账号、组织树和负责人任命，未建授权记录，导致：

1. **部署被拦**：deploy.sh 第 5 步 `check_seed_grants` 三项 FAIL——manager 缺操作授权、leader 18322951923 有 branch 未种子、某 admin 持冗余授权记录（admin 应走职位兜底）。2026-09-09 部署 login-throttle-fix 时即被拦，只能手动绕过上线。
2. **功能缺失**：运行时操作鉴权只看 OperationGrant 表——4 位总监、112 位分公司行政当前无任何业务操作权限；分公司行政无任命也无节点授权，管理数据范围为空（登录后看不到本分公司数据）。

check_seed_grants 自身也有两处口径过时：manager 抽样按 legacy 7 码（含 view_all_notifications=查看抄送记录，岗位模板刻意未给分公司行政），unscoped 预警把"任命已覆盖范围"的总监也列为待补授。

## What Changes

- 新增管理命令 `seed_position_grants`（默认 dry-run，`--apply` 写入，幂等）：
  1. 非 admin 在职用户按**岗位模板**补齐操作码（只补不删，特例保留）
  2. manager/leader 挂有本分公司的补该分公司节点授权
  3. director 范围来自大区负责人任命（任命即授权），不重复建节点记录
  4. 清空 admin 冗余授权记录
  5. 范围仍空者（轮空人员）列人工清单，不猜节点
- `check_seed_grants` 口径现代化：manager/director 抽样改按岗位模板；unscoped 预警排除任命已覆盖者
- 本地库已执行（928 操作码 + 121 节点；幂等复跑全 0；check 转绿），生产随部署执行

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `management-permissions`: 新增"岗位授权批量种子对账"要求——种子命令口径（模板操作码/节点/任命/清理/人工清单）与部署校验口径（模板抽样、任命排除）

## Impact

- **后端**: `apps/permissions/management/commands/seed_position_grants.py`（新增）、`check_seed_grants.py`（口径）、`tests/test_position_permissions.py`（+8 测试）
- **数据**: 生产需跑一次 `seed_position_grants --apply`（约 928 操作码 + 121 节点 + 清 admin 冗余）；3 位轮空 manager（权梦茹/李晴晴/蔡蕾蕾）仍需人工在权限分配页面补授
- 不动模型、API、前端
