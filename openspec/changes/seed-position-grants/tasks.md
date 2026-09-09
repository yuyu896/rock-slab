# 岗位授权批量种子 — 实施任务

## 1. 种子命令

- [x] 1.1 `seed_position_grants` 管理命令：岗位模板操作码补齐（只补不删）+ manager/leader 补本分公司节点 + 清 admin 冗余 + 轮空人工清单；默认 dry-run，`--apply` 写入
- [x] 1.2 幂等：bulk_create ignore_conflicts + 节点存在性检查，重复执行零写入
- [x] 1.3 总监不建节点记录（任命即授权），输出"范围来自任命"与"范围已有"区分

## 2. 校验口径现代化

- [x] 2.1 `check_seed_grants`：manager/director 抽样按 `POSITION_TEMPLATES`（supervisor 退役存量保留 legacy 口径）
- [x] 2.2 unscoped 预警排除任命已覆盖者（按 `resolve_user_scope().is_empty` 判真待人工）

## 3. 测试与验证

- [x] 3.1 单测 +8：dry-run 不写库 / manager 补码+节点+特例保留 / leader 只节点 / 总监补码不建节点 / admin 清理 / 幂等 / 轮空人工清单 / 种子后 check_seed_grants 通过
- [x] 3.2 本地 134 账号实数据：dry-run 计划核对（928 码 + 121 节点 + 4 总监任命 + 3 轮空）→ --apply → 复跑全 0 → check 转绿
- [x] 3.3 后端全量 pytest 627 passed
- [x] 3.4 生产执行：部署新镜像 → dry-run 复核（799 码 + 107 节点 + 清理 admin 冗余 1 节点/9 码）→ --apply → 复跑全 0 → `check_seed_grants` 以 deploy.sh 同款调用（`docker compose run --rm backend`）exit=0 转绿
