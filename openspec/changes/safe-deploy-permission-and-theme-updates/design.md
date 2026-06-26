## Context

生产环境：域名 `qhpanpan.top`（HTTPS, Let's Encrypt）；后端 API `47.97.43.28:8080` 经共享 `root-nginx-1` 反代；Docker Compose 运行后端容器 `rock-slab-backend`，共享 PG 容器 `root-db-1`（库 `rock_slab`，用户 `rock_slab_user`）与 Redis。`deploy.sh` 八步：`git pull → docker build backend → migrate → collectstatic → npm build → up -d backend → nginx reload → health check`。`backend/entrypoint.sh` 启动时也会自动 `migrate`。

备份机制：`/root/backup_db.sh` 每日 03:07 自动 `pg_dump` → `/root/backups/rock_slab_YYYYMMDD_HHMMSS.sql.gz`，保留 14 天；恢复方式 `gunzip < 备份 | docker exec -i root-db-1 psql -U rock_slab_user -d rock_slab`。

本次迁移（`apps/permissions`）：
- 0001 建表（结构，无数据影响）
- 0002 `RunPython` 种子授权（**写数据**，纯新增；`reverse` 清空种子；幂等：`get_or_create`/`ignore_conflicts`）
- 0003 加 `is_all_data` 字段 + 改约束（结构，无数据回填）

约束：生产不可长时间停机；迁移需在低峰；必须有"部署前那一刻"的备份以便精确回滚。

## Goals / Non-Goals

**Goals:**
- 部署前生成即时数据库快照（区别于昨日自动备份）。
- 迁移后立即验证种子授权正确（计数 + 抽样），异常中止。
- 提供清晰的代码回滚与数据回滚两条路径。
- 全程不丢失业务数据。

**Non-Goals:**
- 不改 `deploy.sh` 既有八步顺序与核心逻辑（仅插入备份/验证两步）。
- 不做蓝绿/金丝雀等零停机部署（当前规模无需）。
- 不改迁移本身（迁移已写好且可逆）。
- 不改 Nginx/SSL/DNS 配置。

## Decisions

### 决策 1：部署前用 `/root/backup_db.sh` 做即时备份
在 `deploy.sh` 的 `git pull` **之前**调用 `/root/backup_db.sh`，产出带时间戳的 `rock_slab_*.sql.gz`，并把文件名记录到部署日志。
**Why**：复用既有成熟脚本（与每日自动备份同一逻辑），零额外维护；`pg_dump` 是 PG 官方一致快照。
**Alternatives**：①直连 `docker exec root-db-1 pg_dump` → 与脚本重复（否决）；②`pg_dumpall` → 过重、含其他库（否决）。
**取备份路径**：脚本输出最新文件，部署脚本捕获 `ls -t /root/backups/*.sql.gz | head -1` 作为本次回滚锚点。

### 决策 2：迁移后立即验证种子（不中止主流程，异常告警）
`migrate` 后、`up -d backend` 前，运行一次性校验：
- `ManagementScope.objects.count()` 与 `OperationGrant.objects.count()` > 0（非空）
- 抽样：每个 role 各取一用户，确认其授权与旧 role 隐含一致（supervisor 有 region 授权 + manage_users/manage_categories/manage_assets/approve_*；leader/staff 有 branch 授权；admin 无授权）
通过 `docker compose run --rm backend python manage.py shell -c "..."` 执行；异常则打印告警并退出非零（`set -e` 会阻止后续重启）。
**Why**：种子是 0002 的关键副作用，生产数据若与开发 fixtures 分布不同（如大量无 region/branch 用户），需当场发现。
**Alternatives**：部署后人工抽查 → 发现晚、回滚成本高（否决）。

### 决策 3：回滚分两条独立路径，按问题类型选择
- **代码回滚**（前端样式/页面/逻辑 bug，**数据库正常**）：`git reset --hard <部署前 commit>` → `docker compose build backend` → `npm run build` → `up -d backend` → `nginx reload`。**不动数据库**（新增的 permissions 表/字段保留无害）。
- **数据回滚**（迁移/种子异常或需恢复部署前数据）：`docker compose stop backend` → `gunzip < 部署前备份 | docker exec -i root-db-1 psql ...` → `git reset --hard <部署前 commit>` → 重建重启。
**Why**：大多数问题是前端/逻辑（代码回滚即可，秒级、零数据风险）；只有迁移/种子出错才需数据回滚（分钟级）。区分避免不必要的数据恢复。
**关键**：部署前记录 commit SHA（`git rev-parse HEAD`）与备份文件名，回滚有明确锚点。

### 决策 4：`deploy.sh` 增强 vs 新建 `deploy_safe.sh`
直接在 `deploy.sh` 插入两步（备份在前、验证在 migrate 后），保持单一入口；用变量 `PRE_DEPLOY_COMMIT`、`PRE_DEPLOY_BACKUP` 记录锚点并 echo 出来。
**Why**：避免双脚本维护漂移；本次部署用增强后的 `deploy.sh` 一次性完成。
**Alternatives**：新建 `deploy_safe.sh` → 两套脚本易不一致（否决，但本次先以增强 deploy.sh 为准）。

### 决策 5：低峰部署 + 简短停机说明
`migrate`（~秒级）+ `up -d backend` 重启期间接口可能短暂 502/超时；选低峰窗口执行，部署前可选地在 Nginx 临时返回维护页（本次不做，仅文档提示）。
**Why**：当前迁移快、停机短，维护页属过度设计；仅记录预期。

## Risks / Trade-offs

- **[迁移期间接口短暂不可用]** → 选低峰窗口；`entrypoint.sh` 启动自动 migrate 会在每次重启跑（幂等，无副作用）。
- **[种子在生产数据上覆盖不全]** → 决策 2 的迁移后校验当场发现；无 region/branch 的非 admin 用户会被 0002 记录日志（开发期已观测到 6 例），部署后用"权限分配"页面人工补授。
- **[回滚后代码与 DB schema 不匹配]** → permissions 表/字段是新增，旧代码不引用它们，回滚后保留无害；若回滚到完全不认识 permissions app 的旧 commit，表仍存在但无人查询，安全。
- **[备份文件体积/磁盘]** → 每次部署多一个备份（与每日备份同体积）；14 天自动清理仍生效；部署前 `df -h` 确认磁盘。
- **[pg_dump 与运行中写入的一致性]** → `pg_dump` 取事务一致快照，不锁表，不影响在线读写。

## Migration Plan（部署执行步骤）

1. **本地准备**：确认所有改动已 commit 并 `git push origin main`；记录待部署 commit SHA。
2. **服务器执行**（SSH 到 `47.97.43.28`，`cd /root/rock-slab`）：
   1. 记录锚点：`PRE_COMMIT=$(git rev-parse HEAD)`；`df -h /` 确认磁盘。
   2. **即时备份**：`/root/backup_db.sh`；`PRE_BACKUP=$(ls -t /root/backups/*.sql.gz | head -1)`；echo 两者。
   3. `bash deploy.sh`（增强版会在 git pull 前备份、migrate 后验证）。
   4. 部署后冒烟：`curl /api/health/` → 200；浏览器登录 → 资产/品目/盘点/权限分配各点一遍。
3. **异常处理**：
   - 前端/逻辑异常 → 代码回滚（决策 3①）。
   - 迁移/种子/数据异常 → 数据回滚（决策 3②），用 `PRE_BACKUP` 恢复。
4. **收尾**：核对无 region/branch 用户清单（0002 日志），在权限分配页面补授。

## Open Questions

- 是否需要部署前在 Nginx 临时挂维护页？（默认不挂，停机 < 30s）
- 种子校验失败时是"中止部署"还是"告警继续"？（默认中止，由人工判断后重试）
