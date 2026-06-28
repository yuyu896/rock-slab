## Context

生产 `qhpanpan.top` 当前 = `4fd2211`（已上线，含权限解耦/白蓝/页面化/增强 deploy.sh）。本地 HEAD = `86291d1`，领先 origin/main 共 7 个提交（安全加固/并发/报表/导入/审计整改）+ 4 个未提交报表文件。这批改动**无数据库迁移**（已核实 `4fd2211..HEAD` 及未提交 diff 均无 migrations/），`settings` 仅加常量/可选配置（`DATA_UPLOAD_MAX_MEMORY_SIZE`/`FILE_UPLOAD_MAX_MEMORY_SIZE`=60MB、`NUM_PROXIES` 默认 1、密码 `min_length=8`），**无新增必需环境变量**。

部署基础设施就绪：增强版 `deploy.sh`（部署前 `/root/backup_db.sh` 即时备份 + 迁移后 `check_seed_grants` 校验 + 末尾打印 commit/备份双轨回滚锚点）已在 `4fd2211` 上线。服务器工作区此前清理过（`useFocusTrap.ts`/`useTable.ts`/`nginx/rock-slab.conf` 已移至 `/root/rock-slab-local-backup`），分支为 `master` 跟随 `origin/main` 快进。

## Goals / Non-Goals

**Goals:**
- 把 7+1 个提交安全部署到生产，获得安全加固与质量修复。
- 部署前即时备份（即使无迁移，也保留快照兜底）。
- 针对新功能做重点冒烟，发现问题能秒级代码回滚。

**Non-Goals:**
- 不做 DB 迁移（本次无）。
- 不改部署脚本（复用既有增强版）。
- 不做蓝绿/金丝雀（规模无需）。
- 不改 nginx/SSL/DNS。

## Decisions

### 决策 1：先提交未提交改动 + 顺手修前后端密码长度不一致，再统一 push
4 个报表文件（`reports/urls.py`、`reports/views.py`、`api/reports.ts`、`Reports.vue`）属审计整改变更的一部分；另核查发现前端 `PasswordChangeModal` 密码长度提示/校验（6 位）与后端 `min_length=8` 不一致——部署前已修复（占位符"至少6位"→"至少8位"、前端校验 `< 6`→`< 8`）。两者一并 commit，确保部署内容完整、可回滚到干净锚点。
**Why**：未提交改动在服务器 `git pull` 后会丢失/冲突；密码长度不一致会让用户输 6-7 位时被前端放行、后端拒绝，体验矛盾，必须在上线前对齐。

### 决策 2：直接复用既有增强版 `deploy.sh`，不改脚本
上次已上线的 `deploy.sh` 含备份+校验+回滚三件套，本次无迁移，脚本无需任何调整。`migrate` 步骤会是 no-op（无新迁移），`check_seed_grants` 仍运行（应继续通过，因种子数据未变）。
**Why**：避免引入新风险；脚本已验证可靠。

### 决策 3：回滚仅需代码路径（无需数据恢复）
因无 DB 迁移，若部署后发现 bug，用 `deploy.sh` 末尾打印的 **代码回滚命令**（`git reset --hard <PRE_DEPLOY_COMMIT>` + rebuild + 重启）即可，**不动数据库**。数据回滚路径本次不需要（无迁移/种子变更），但脚本仍会打印备份锚点以备万一。
**Why**：无迁移=无数据风险，代码回滚秒级、零数据副作用。

### 决策 4：冒烟清单聚焦本次新功能（而非全量回归）
重点验证本次改动的 6 个功能域，而非逐页面回归（上次已全量验过）：
1. 登录限流（5次/分钟）+ 账号锁定
2. 密码强度（弱密码被拒，最小 8 位）
3. 资产/固定资产导入（大文件 60MB、按列名映射）
4. 报表数据隔离（非 admin 按授权范围看报表）
5. 审批并发（重复提交幂等、库存行锁）
6. 上传校验（非法文件被拒）

### 决策 5：部署前告知用户"预期行为变化"
本次安全加固会改变若干用户可感知行为（弱密码被拒、登录失败锁定、大文件可上传），属预期效果。部署后通知用户，避免被当 bug。
**Why**：安全行为变化若不预告，用户可能误报"登录坏了/改不了密码"。

## Risks / Trade-offs

- **[认证/并发逻辑 bug 导致登录或审批异常]** → 决策 4 的冒烟清单逐项验证；异常走代码回滚（秒级）。
- **[`NUM_PROXIES` 默认 1 与实际代理层数不符导致限流误判]** → 线上经 root-nginx-1 单层反代，`NUM_PROXIES=1` 正确；若发现限流按容器 IP 聚集，调 `.env` 的 `NUM_PROXIES`。
- **[弱密码策略导致既有弱密码用户无法改密码]** → 属预期；如需放宽，调 `AUTH_PASSWORD_VALIDATORS` 的 `min_length`。
- **[前后端密码长度阈值不一致（前端 6 / 后端 8）]** → 已在部署前修复前端为 8 位（决策 1），消除"输 6-7 位被前端放行、后端拒绝"的矛盾体验。
- **[大文件上传触发 nginx `client_max_body_size` 限制]** → Django 已放宽到 60MB，需确认 nginx 层 `client_max_body_size` ≥ 60MB（部署后核对）。
- **[报表权限隔离收窄，某用户突然看不到原报表数据]** → 属预期（修复越权）；核对授权范围正确即可。

## Migration Plan（部署执行步骤）

1. **本地**：`git add` 4 个报表文件 + commit；`git push origin main`；记录待部署 SHA。
2. **服务器**（SSH，低峰窗口）：
   1. `cd /root/rock-slab`；记录 `PRE_DEPLOY_COMMIT=$(git rev-parse HEAD)`（应为 `4fd2211`）。
   2. `df -h /` 确认磁盘。
   3. `bash deploy.sh`：自动备份→pull 到新 SHA→build→migrate(no-op)→check_seed_grants→collectstatic→npm build→重启→nginx reload→健康检查→打印回滚锚点。
3. **冒烟**：按决策 4 清单逐项验证（重点登录/导入/报表/审批）。
4. **异常**：用末尾打印的**代码回滚命令** `git reset --hard $PRE_DEPLOY_COMMIT` + rebuild + 重启（无需数据恢复）。
5. **收尾**：告知用户预期行为变化；观察后端日志 24h。

## Open Questions

- nginx 层 `client_max_body_size` 是否已 ≥ 60MB？（部署后核对，不足则调整 nginx 配置）
- 是否需要预告用户"密码强度/登录锁定"策略变化？（建议预告，避免误报）
