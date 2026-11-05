# 磐盘生产部署文档

磐盘（Rock Slab）资产管理系统生产环境部署与运维文档。发布指引最后核对：2026-11-04；基础设施说明核验截至：2026-06-15。

> **发布提示：** 本文的基础设施说明仍以 2026-06-15 为准。每次发布的候选版本、迁移和数据操作清单，以同目录的 `RELEASE_BASELINE.md` 为准。`deploy.sh` 会从 `origin/main` 拉取代码、执行 schema migration 并重启服务，没有 dry-run 模式；它不会自动迁移旧权限、应用岗位基线或调整数据范围。候选尚未合入 `origin/main`、发布基线中的人工核对未完成或生产工作树改动未保全时，不要运行。不要照抄本文旧的手动拉代码/构建步骤，也不要重复执行第 8 节中的一次性台账迁移命令。

## 1. 概览

| 项 | 值 |
|----|----|
| 访问地址 | https://qhpanpan.top |
| 服务器 | 阿里云 ECS 47.97.43.28（CentOS Stream 9） |
| DNS | qhpanpan.top / www.qhpanpan.top → 47.97.43.28（阿里云解析） |
| 代码仓库 | https://github.com/yuyu896/rock-slab |
| 技术栈 | Django 5.1 (Gunicorn) + Vue 3 (Vite) + PostgreSQL + Redis + Docker + Nginx |

## 2. 架构（重要）

服务器上跑着**两个项目**，都是 Docker Compose 栈。磐盘复用了 AI销售教练（xsjqr）项目的共享基础设施。

```
浏览器
  │
  ▼ HTTPS:443
root-nginx-1（AI销售教练项目的 nginx 容器，占公网 80/443）
  │  配置：/root/nginx.conf（含 qhpanpan.top 和 xsjqr.top 两个 server 块）
  │  qhpanpan.top 的 HTTPS → proxy_pass http://172.18.0.1:8080
  ▼
rock-slab-nginx（磐盘 nginx，监听 8080，仅本机）
  │  配置：/root/rock-slab/nginx/rock-slab.conf
  │  服务前端 dist + /api 反代 + /media + /static
  ▼ /api/ → proxy_pass http://127.0.0.1:8002
rock-slab-backend（磐盘后端 Gunicorn，监听 8002，host 网络）
  │
  ├── PostgreSQL：root-db-1 容器（pgvector:pg16，127.0.0.1:5432，共享）
  └── Redis：root-redis-1 容器（127.0.0.1:6379，共享）
```

**关键点**：
- 公网入口是 `root-nginx-1`（不是磐盘自己的 nginx），它做 SSL 终止并按 server_name 路由
- `root-nginx-1` 通过 Docker 网关 `172.18.0.1:8080` 访问磐盘 nginx
- 磐盘后端用 `network_mode: host`，直接监听宿主机 8002

## 3. 访问凭据

> ⚠️ 真实密码不在本文档，统一在服务器 `/root/rock-slab/.env`（gitignore 保护）

| 项 | 位置 |
|----|------|
| 服务器 SSH | `ssh root@47.97.43.28` |
| 后端环境变量 | `/root/rock-slab/.env`（SECRET_KEY / DATABASE_URL / REDIS_URL / ALLOWED_HOSTS / PORT=8002 / SECURE_SSL_REDIRECT=False） |
| PostgreSQL 连接 | 见 .env 的 DATABASE_URL（库 rock_slab / 用户 rock_slab_user） |

## 4. 关键路径

| 内容 | 路径 |
|------|------|
| 项目代码 | `/root/rock-slab/` |
| 后端生产配置 | `/root/rock-slab/.env` |
| 公网 nginx 配置 | `/root/nginx.conf`（root-nginx-1 挂载为 /etc/nginx/conf.d/default.conf） |
| 磐盘 nginx 配置 | `/root/rock-slab/nginx/rock-slab.conf` |
| 前端构建产物 | `/root/rock-slab/frontend/dist/`（rock-slab-nginx 挂载） |
| SSL 证书 | `/etc/letsencrypt/live/qhpanpan.top/` |
| 数据库备份 | `/root/backups/`（每日自动，保留 14 天） |
| 备份脚本 | `/root/backup_db.sh` |

## 5. 常用运维命令

```bash
cd /root/rock-slab

# ===== 发布（先审阅 RELEASE_BASELINE.md 与当前候选）=====
# 仅在 RELEASE_BASELINE.md 的发布门槛完成后，于维护窗口执行。
# deploy.sh 会先备份数据库，再拉取 origin/main、构建后端、执行 schema migration 和检查、构建前端并重启服务；没有 dry-run 模式。
# 旧权限码迁移、岗位基线应用及数据范围调整需单独审阅和批准，不由此脚本执行。
# bash deploy.sh

# ===== 日志 =====
docker logs -f --tail 50 rock-slab-backend   # 后端实时日志
docker logs -f --tail 50 rock-slab-nginx     # 磐盘 nginx 日志

# ===== 健康 & 登录验证 =====
curl https://qhpanpan.top/api/health/        # 应返回 {"status": "ok"}

# ===== Nginx（公网 root-nginx-1）=====
docker exec root-nginx-1 nginx -t            # 测试配置语法
docker exec root-nginx-1 nginx -s reload     # 重载配置

# ===== SSL 证书 =====
certbot certificates                         # 查看证书状态与到期时间
# 续期由 certbot 自动处理（pre/post hook 会停启 root-nginx-1）

# ===== 数据库备份 =====
/root/backup_db.sh                           # 手动立即备份
ls -lht /root/backups/                       # 查看备份文件
cat /root/backups/backup.log                 # 查看备份日志

# ===== 数据库恢复（从备份）=====
# gunzip < /root/backups/rock_slab_YYYYMMDD_HHMMSS.sql.gz | \
#   docker exec -i root-db-1 psql -U rock_slab_user -d rock_slab

# ===== 前端重新构建（前端有改动时）=====
cd /root/rock-slab/frontend && npm install && npm run build
# dist/ 由 rock-slab-nginx 直接服务，无需重启
```

## 6. 已知坑点（部署时踩过的）

1. **登录 401（带旧 token）** — 登录视图原本会被 DRF 默认 Token 认证拦截。已加 `@authentication_classes([])` 修复。
2. **登录 500（孤儿 token）** — 多表继承下旧代码在基础表留了没有子表行的孤儿 token。已加 `get_or_create_token` 防孤儿/防竞态。如再触发，清理孤儿：
   ```bash
   docker compose exec backend python manage.py shell -c "
   from rest_framework.authtoken.models import Token as B
   from apps.authentication.models import ExpiringToken as E
   B.objects.exclude(user_id__in=E.objects.values_list('user_id',flat=True)).delete()"
   ```
3. **pip 构建超时** — 国内服务器访问国际 PyPI 极慢。Dockerfile 已改用阿里云镜像 `https://mirrors.aliyun.com/pypi/simple/`。
4. **端口** — 后端固定 8002（gunicorn 绑定、nginx 反代、healthcheck、deploy.sh 全部对齐）。host 网络模式下 docker-compose 的 `ports` 无效，已移除。
5. **8080 端口** — 磐盘 nginx 的另一入口，已用 firewalld 关闭公网访问；外部只走 443。
6. **nginx reload** — `docker exec root-nginx-1 nginx -s reload` 是对的（nginx 在容器里），**不要**改成 systemctl。

## 7. 日常维护检查清单

- [ ] 每周：`certbot certificates` 确认证书未过期
- [ ] 每周：`ls -lht /root/backups/` 确认备份在自动生成
- [ ] 每月：`docker system prune` 清理无用镜像（注意别删在用的）
- [ ] 关注服务器安全组/防火墙，5432/6379/3306 等数据库端口不应对公网开放

## 8. 历史步骤：P1 台账契约上线（资产模型 V2）

本节保留作历史记录，不是当前部署流程。`migrate_initial_ledger --confirm-backup` 属于一次性存量数据迁移；不得因常规发版再次执行。当前候选的数据库和独立数据操作以 `RELEASE_BASELINE.md` 为准，日常部署流程以 `deploy.sh` 为准。
