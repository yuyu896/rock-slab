# design — 岗位授权批量种子

## 口径依据

权限体系口诀：**岗位定操作、任命定范围、特例才单独授予**。

- 操作码：运行时鉴权只看 `OperationGrant` 表（`User.can` / OperationPermission，admin 恒真）——所以总监/行政补码是功能刚需
- 范围：`resolve_user_scope` = 授权记录（ManagementScope）∪ 树负责人任命（Region.manager / Team.leader / Branch.manager）——总监任大区负责人已天然有范围，**不重复建节点记录**（铁律"每样信息只存一处"：任命是范围的事实源）
- manager（分公司行政）无任命 → 必须建节点授权；user.branch 是导入时的归属事实 → 补本分公司节点（模板 scope_type='branch' 同口径）

## 关键取舍

| 问题 | 决定 | 理由 |
|------|------|------|
| manager 操作码按 legacy 7 码还是岗位模板 8 码？ | 岗位模板 | legacy 多出的 `view_all_notifications`（查看抄送记录）是模板刻意不给分公司行政的（通知按范围可见）；模板是现行唯一权威。同步把 check_seed_grants 的 manager 抽样从 legacy 升级为模板，否则门禁与种子口径互相矛盾 |
| director 要不要也建 ManagementScope？ | 不建 | 任命即授权已覆盖；再建节点记录 = 范围信息存两份，且未来换任时要同步两处 |
| leader 建分公司节点还是行政组节点？ | 分公司节点 | check_seed_grants 既有要求（有 branch 应有 branch 授权）；导入时 leader 挂在分公司；与组任命取并集无损失 |
| 轮空人员（无 branch 无任命） | 列清单不猜 | 组织归属是业务决定，脚本猜节点等于编数据；留给权限分配页面人工补授（WARN 不拦部署） |
| admin 持有的授权记录 | 删除 | admin 运行时恒真，记录纯冗余且触发门禁 FAIL；删除零损失 |

## 命令形态

参照 `migrate_positions` 先例：管理命令、默认 dry-run 逐人打印计划、`--apply` 写入、只补不删、幂等（bulk_create ignore_conflicts + 同节点存在性检查）。每行输出：`姓名（手机号）：岗位 ｜ 补授操作码 ｜ 范围动作`，摘要含待人工与 admin 清理计数。

## 部署顺序（鸡生蛋问题）

deploy.sh 在第 5 步被 check_seed_grants 拦截，而种子命令随新镜像才可用。顺序：手动 `build + up -d`（镜像含新命令）→ `docker compose run --rm backend python manage.py seed_position_grants`（dry-run 复核）→ `--apply` → check 转绿 → 此后 deploy.sh 全流程恢复畅通。

## 验证记录（本地，134 账号实数据）

- dry-run：928 操作码（116 人 × 8 码）+ 121 节点 + 4 总监"范围来自任命" + 3 轮空待人工
- --apply 后复跑：全 0（幂等 ✓）
- `check_seed_grants`：**校验通过 ✓**（仅剩 3 轮空 WARN）
- 后端全量 pytest 627 passed
