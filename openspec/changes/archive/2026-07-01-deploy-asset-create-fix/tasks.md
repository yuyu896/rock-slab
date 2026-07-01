## 1. 本地提交与推送

- [x] 1.1 核实 `git status`：改动仅 `backend/apps/assets/serializers.py`、`backend/tests/test_asset_crud.py`、`backend/tests/test_fixed_asset.py`、`openspec/changes/fix-asset-create-400/`、`openspec/changes/deploy-asset-create-fix/`、`openspec/changes/redeploy-security-and-quality-hardening/tasks.md`
- [x] 1.2 确认**无新迁移文件**（`git status` 不含 `backend/apps/assets/migrations/` 新文件）
- [x] 1.3 `git add` 仅上述目标文件，**排除 `.claude/settings.local.json`**
- [x] 1.4 `git commit`（消息说明：修复新增固定资产/资产 400 + 资产编号分类校验，部署上线）
- [x] 1.5 `git push origin main`
- [x] 1.6 确认 `origin/main` 已更新到新 commit、`origin/main..HEAD` 为空

## 2. 服务器部署

- [x] 2.1 SSH 登录生产服务器 `47.97.43.28`
- [x] 2.2 `cd /root/rock-slab && bash deploy.sh`
- [x] 2.3 观察 9 个步骤全部成功、健康检查 `GET /api/health/` 返回 200
- [x] 2.4 记录控制台打印的回滚锚点（部署前 commit SHA + 部署前备份路径）

## 3. 部署后验证（生产 `qhpanpan.top` 真实数据）

- [x] 3.1 `https://qhpanpan.top/api/health/` 返回 200
- [x] 3.2 新增固定资产（仅填一个已存在的资产编号）→ 创建成功（201 / 列表可见）
- [x] 3.3 新增固定资产填一个品目表不存在的资产编号 → 提示"资产编号不存在"、不创建
- [x] 3.4 新增资产（不填序号、选分公司）→ 创建成功，序号自增、分公司正确关联
- [x] 3.5 新增资产填一个未在资产分类登记的编号 → 提示"该资产编号未在资产分类登记"、不创建
- [x] 3.6 资产列表、固定资产列表、资产分类列表正常加载（回归无破坏）

## 4. 回滚预案（仅在冒烟发现严重问题时执行；本次部署成功，未触发）

- [x] 4.1 执行 `deploy.sh` 末尾打印的**代码回滚命令**（`git reset --hard <部署前 commit> && docker compose build backend && (前端 rebuild) && docker compose up -d backend && nginx -s reload`）
- [x] 4.2 确认回滚后生产行为恢复到部署前（无需数据库恢复）

## 5. deploy.sh 修复（部署中发现的脚本缺陷）

- [x] 5.1 `entrypoint.sh` 增加 `exec "$@"` 分支：传入命令时直接执行，不再硬跑 gunicorn 抢 8002
- [x] 5.2 `deploy.sh` 第 4/5/6 步去掉不生效的 `--entrypoint python`，改 `docker compose run --rm backend python manage.py ...`
- [x] 5.3 `deploy.sh` 增加 self-reexec：git pull 后若自身被更新则重执行新版（继承 `PRE_DEPLOY_COMMIT`），解决"运行时旧版 deploy.sh"
- [x] 5.4 服务器部署验证：`bash deploy.sh` 第 4 步不再卡，9 步全绿、`health: 200`
