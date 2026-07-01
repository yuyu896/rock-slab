## Context

生产 `qhpanpan.top` 运行在 `e43cb37`（三层架构：root-nginx-1 公网 443 → rock-slab-nginx 8080 → rock-slab-backend Gunicorn 8002，共享 root-db-1 / root-redis-1）。本地此后完成 `fix-asset-create-400`：修复新增固定资产/资产 400 + 资产编号分类校验，**纯后端 serializer 层、+53 行、零迁移**，已有 39 + 68 项测试覆盖、本地前后端冒烟通过。

现网 `deploy.sh` 是增强版（部署前 DB 备份 + 迁移后 `check_seed_grants` + 末尾自动打印代码/数据回滚锚点命令），已在 `e43cb37` 随之上线，本次直接复用。

工作区当前未提交：`backend/apps/assets/serializers.py`、`backend/tests/test_asset_crud.py`、`backend/tests/test_fixed_asset.py`、`openspec/changes/fix-asset-create-400/`、`openspec/changes/redeploy-security-and-quality-hardening/tasks.md`（另一变更的进度文档）、`.claude/settings.local.json`（本地 IDE 配置）。无未推送提交（`origin/main..HEAD` 为空）。

## Goals / Non-Goals

**Goals:**
- 把 `fix-asset-create-400` 的后端修复安全上线到 `qhpanpan.top`，消除新增固定资产/资产的 400 阻断。
- 部署过程零数据风险（无迁移）、可秒级回滚。
- 部署后用针对性冒烟验证修复在生产生效。

**Non-Goals:**
- 不部署前端（本次无前端改动）。
- 不改 DB schema、nginx 站点、SSL、权限模型。
- 不归档 `fix-asset-create-400`（归档与部署独立，可后续单独 `/opsx:archive`）。
- 不处理 `redeploy-security-and-quality-hardening` 的未完成实施（那是另一个变更）。

## Decisions

### 决策 1：提交范围严格控制
本次 commit 仅含 `fix-asset-create-400` 的生产代码与 openspec 文档：`serializers.py`、两个测试文件、`openspec/changes/fix-asset-create-400/`、本部署提案目录。**排除** `.claude/settings.local.json`（本地 IDE 配置，不应进仓库）。`redeploy-security-and-quality-hardening/tasks.md` 是另一变更的进度文档、与生产行为无关，**一并提交**以保持工作区干净（也可单独提交，不影响部署）。

### 决策 2：复用现网 `deploy.sh`，不手动逐步
直接 SSH 执行 `bash deploy.sh`，它已封装备份→pull→build→migrate→check_seed_grants→collectstatic→npm build→重启→nginx reload→健康检查，并在末尾打印回滚锚点。手动逐步反而易漏步骤、绕过备份。

### 决策 3：部署后冒烟聚焦修复点
健康检查（`/api/health/` 200）只证明进程活着；本次重点验证三条修复路径在生产真实数据上生效（见 tasks 第 4 节）。

### 决策 4：无迁移 → 纯代码回滚
本次 `migrate` 为 no-op，回滚**仅需代码层**：`git reset --hard <部署前 commit>` + rebuild backend + 重启 + nginx reload（`deploy.sh` 末尾自动给出该命令）。无需动数据库备份。

## Risks / Trade-offs

- **[资产编号分类校验改变线上操作习惯]** → 上线后，用「未在资产分类登记的编号」创建资产会被 400 拒绝。这是修复的预期效果，但需告知习惯手填任意编号的用户：请先在「资产分类」登记编号。**Mitigation**：错误提示已明确「请先在资产分类中添加」。
- **[update 路径误伤历史脏数据]** → `AssetSerializer.validate()` 对更新仅在请求携带 `资产编号` 时校验；PATCH 改其他字段不触发。已由测试覆盖，历史脏数据更新其他字段不受影响。
- **[序号自增并发竞态]** → 与既有 `warehouse()` 路径同风险、同等级，本次不引入新风险。
- **[前端 npm build 产物变化]** → 前端代码无改动，重建产物应一致；若产物 hash 变化导致浏览器缓存，用户硬刷新即可，无功能影响。

## Migration Plan

1. **本地**：`git add` 仅 fix-asset-create-400 相关文件 + openspec 文档（含本提案、redeploy tasks 进度）；`git commit`；`git push origin main`。
2. **服务器**：`cd /root/rock-slab && bash deploy.sh`，观察 9 步全绿、健康检查 200、回滚锚点打印。
3. **验证**：按 tasks 第 4 节冒烟（含用真实生产数据测三条修复路径）。
4. **回滚（如异常）**：执行 `deploy.sh` 末尾打印的代码回滚命令；无需数据恢复。

## Open Questions

- 部署时机：是否立即部署，还是等某个时间窗口？默认得到确认后即部署（停机秒级，影响小）。
