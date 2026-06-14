## Context

磐盘是基于 Django 5.1 (Gunicorn) + Vue 3 (Vite) + PostgreSQL + Redis + Docker + Nginx 的固定资产管理系统，部署在阿里云 ECS (47.97.43.28)。

**当前实测状态**（2026-06-14）：
- 后端 API 在 `47.97.43.28:8080` 健康，但端口直接暴露公网（admin 可外部访问）
- DNS 已生效（qhpanpan.top / www.qhpanpan.top → 47.97.43.28）
- Nginx 监听 443，但域名 HTTPS 握手失败（SSL 证书未正确签发/损坏）
- 代码库有 5 个未提交的迁移文件 + 缺失 CSRF 配置 + PORT 冲突 + 无 entrypoint + 无 git remote
- 前端当前可正常构建（Transfer 类型已补全，vue-tsc 0 错误）—— 这一点与之前的提案不同，前端已不是阻塞项

**技术约束**：docker-compose.yml 使用 `network_mode: host`（容器直接用宿主机网络，ports 映射被忽略）；PostgreSQL/Redis 计划宿主机直接安装。

## Goals / Non-Goals

**Goals:**
- 修复全部代码层面阻塞项并提交（含迁移文件）
- 配置 git 远程仓库，支持 deploy.sh 一键部署
- 服务器搭建 PostgreSQL/Redis/防火墙
- Docker 部署后端 + 构建前端
- 新增 Nginx 虚拟主机并**修复 SSL 证书**，使 https://qhpanpan.top 可正常访问
- 关闭 8080 外部访问
- 完成端到端验证

**Non-Goals:**
- CI/CD 自动化流水线（后续迭代）
- 多环境部署 / staging
- CDN / 数据库高可用 / Kubernetes
- 邮件服务配置
- 前端 Element Plus 按需引入优化（非阻塞）
- 将 PostgreSQL/Redis 容器化（当前选宿主机安装）

## Decisions

### 1. 迁移文件必须先提交
**选择**: 在任何部署前，`git add` 并 commit 5 个未跟踪迁移文件（assets 0004/0005、organizations 0004、transfers 0006/0007）。
**理由**: deploy.sh 靠 `git pull` 取代码，未跟踪文件不会进入服务器，导致模型与数据库 schema 不一致，migrate 会报错或数据错乱。这是最高优先级。

### 2. PostgreSQL / Redis 宿主机直接安装
**选择**: 宿主机安装，Docker 仅运行 Django 后端。
**理由**: docker-compose.yml 只定义 backend 服务；.env.example 的 DATABASE_URL/REDIS_URL 指向 localhost；host 网络模式下容器可直接访问宿主机 localhost。单服务器场景更易调试备份。

### 3. Nginx 宿主机运行 + 新增虚拟主机
**选择**: 用宿主机已运行的 Nginx，新增磐盘 vhost，保留 AI销售教练项目。
**理由**: Nginx 已在 443 监听。两个项目通过 server_name 区分（磐盘走域名，AI销售教练走 IP）。deploy.sh 中 `docker exec root-nginx-1 nginx -s reload` 是错的，需改为 `systemctl reload nginx` 或 `nginx -s reload`。

### 4. SSL 证书：certbot 重新签发
**选择**: 用 Let's Encrypt certbot 为 qhpanpan.top（及 www）签发证书，修复当前损坏的证书。
**理由**: 当前域名 HTTPS 握手失败，证书未正确签发或与域名不匹配。nginx/qhpanpan.top.conf 已预留 `/etc/letsencrypt/live/qhpanpan.top/` 路径。先上 HTTP-only 配置，certbot webroot 验证签发，再启用 SSL。

### 5. PORT 统一为 8002
**选择**: 统一所有端口为 8002：.env 设 PORT=8002 → gunicorn 绑 0.0.0.0:8002 → nginx proxy_pass 127.0.0.1:8002 → 健康检查 localhost:8002 → deploy.sh 检查 8002。
**理由**: 当前 gunicorn 读 PORT（8002），但 docker-compose 健康检查用 8000，deploy.sh 用 8002，三处不一致。host 网络模式下 gunicorn 实际监听 PORT 指定的端口，必须全部对齐到 8002。

### 6. 添加后端 entrypoint.sh
**选择**: 新建 backend/entrypoint.sh，启动前执行 `migrate`，Dockerfile 设为 ENTRYPOINT。
**理由**: Dockerfile 直接 CMD gunicorn，容器重启不会迁移。entrypoint 确保每次启动 schema 最新。

### 7. SECURE_SSL_REDIRECT 保持由 env 控制（部署时设 False）
**选择**: 部署时在 .env 设 `SECURE_SSL_REDIRECT=False`（Nginx 已处理 HTTP→HTTPS）。
**理由**: production.py 默认 True，会导致直连 Gunicorn 的健康检查被 301 重定向到 HTTPS（而 Gunicorn 不服务 HTTPS），健康检查失败。Nginx 已做重定向，Django 层无需再做。

### 8. 前端构建当前已可用，无需改动
**选择**: 不动前端构建配置（vue-tsc -b 当前 0 错误，Transfer 类型已补全）。
**理由**: 实测前端可正常 `npm run build`。categories.ts:46 和 ImportDialog.vue:40 的 raw fetch() 是 WARNING（绕过 401 拦截器），不阻塞部署，可后续优化。

## Risks / Trade-offs

- **[迁移文件未提交]** → 最高风险。若漏 commit，部署后 schema 不一致。必须先全部 add+commit。
- **[SSL 证书损坏]** → 当前域名 HTTPS 不可用。certbot 重新签发前需确保 80 端口可被 Let's Encrypt 验证（HTTP-only 配置 + webroot 目录）。
- **[8080 暴露]** → 后端直接公网可访问，admin 裸奔。防火墙必须关闭 8080。
- **[端口冲突]** → host 网络模式 + PORT 不一致会导致健康检查失败、nginx 代理 502。必须统一 8002。
- **[静态文件]** → collectstatic 写入容器内，volume mount `./backend/staticfiles:/app/staticfiles` 可能被空宿主目录覆盖。部署时需确保宿主 staticfiles 目录有内容。
- **[host 网络模式]** → ports 映射被忽略，端口隔离弱，需靠防火墙兜底。

## Open Questions

1. **Git 平台选择**: GitHub / Gitee / 阿里云 Codeup？（影响服务器拉代码方式）
2. **SSH 访问方式**: 密码还是密钥？
3. **服务器已装软件**: PostgreSQL、Redis、Node.js、certbot 是否已安装？需 SSH 检查。
4. **当前损坏证书的处理**: 是否需要先删除 `/etc/letsencrypt/live/qhpanpan.top/` 旧证书再重新签发？
5. **AI销售教练项目**: 确认保留（已决定新增 vhost 而非替换）。
