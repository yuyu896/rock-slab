## 1. 提交未跟踪的迁移文件（最高优先级阻塞项）

- [ ] 1.1 `git add` 5 个未跟踪迁移文件：assets/migrations/0004、0005；organizations/migrations/0004；transfers/migrations/0006、0007
- [ ] 1.2 确认 `git status` 中 migrations/ 目录下无 `??` 未跟踪项
- [ ] 1.3 commit 这些迁移文件（确保进入 git 历史，deploy.sh 的 git pull 才能拿到）
- **实际状态**：服务器 DB 已有数据（迁移曾以其他方式应用过），但**代码仓库仍未提交**这 5 个文件，未来 git pull 部署会丢。待办。

## 2. 代码修复 — 后端阻塞项

- [ ] 2.1 在 production.py 添加 `CSRF_TRUSTED_ORIGINS = ['https://qhpanpan.top', 'https://www.qhpanpan.top']`
- [x] 2.2 在 production.py 补全 ALLOWED_HOSTS，加入 www.qhpanpan.top
- [x] 2.3 统一端口为 8002
- [ ] 2.4 新建 backend/entrypoint.sh — 启动前执行 `python manage.py migrate --noinput`，Dockerfile 设为 ENTRYPOINT
- [ ] 2.5 更新 .env.example — 补充 SECURE_SSL_REDIRECT=False、GUNICORN_WORKERS 等说明
- [x] **2.6（新增）登录视图加 `@authentication_classes([])`** — 修复登录带旧 token 时 401 的 bug（views.py 已改，需重新部署生效）
- **实际状态**：2.2/2.3 在服务器 .env 层面已达成；2.1/2.4/2.5/2.6 在本地代码仓库待提交。

## 3. 代码修复 — deploy.sh

- [x] 3.1 修正 Nginx reload 命令
- [x] 3.2 确认 deploy.sh 健康检查端口为 8002
- **实际状态（推翻原判断）**：nginx 确实在 `root-nginx-1` 容器里，所以原 `docker exec root-nginx-1 nginx -s reload` **本来就是对的**，无需改成 systemctl。3.1/3.2 维持原样即可。

## 4. Git 远程仓库配置

- [ ] 4.1 在选定平台（GitHub/Gitee/阿里云 Codeup）创建远程仓库
- [ ] 4.2 配置本地 `git remote add origin <url>`
- [ ] 4.3 推送 main 分支（含迁移文件和代码修复），确认远程有全部 5 个迁移文件
- **实际状态**：项目当前以 /root/rock-slab/ 目录形式存在于服务器（疑似 tar.gz 解压），**未走 git**。未来要支持 deploy.sh 一键部署，必须配 remote。待办。

## 5. 服务器环境检查与准备

- [x] 5.1 SSH 登录 47.97.43.28，确认系统版本、已装软件（docker ps、nginx -t、systemctl status postgresql/redis、node --version、certbot --version）
- [x] 5.2 安装缺失软件：Docker、Docker Compose、Node.js LTS、certbot（已装则跳过）
- [x] 5.3 安装配置 PostgreSQL
- [x] 5.4 安装启动 Redis
- [ ] 5.5 配置防火墙 — 仅开放 22/80/443，**关闭 8080 外部访问**（当前 admin 裸奔），同时关闭 8002/5432/6379
- [x] 5.6 检查 AI销售教练项目 Nginx 配置位置，确认 server_name 和端口分配（保留不动）
- **实际状态（推翻原假设）**：PG/Redis **不是宿主机安装**，而是共享 AI销售教练的 Docker 容器 `root-db-1`(pgvector:5432) 和 `root-redis-1`(6379)。磐盘连的是这两个共享容器。Docker/compose/certbot 已装；**Node.js 未装宿主机**（但前端 dist 已构建，暂不影响）。**5.5 防火墙未做，8080 仍裸奔**——高优先级待办。

## 6. 项目部署到服务器

- [x] 6.1 在服务器部署项目到 /root/rock-slab/
- [x] 6.2 创建 .env 生产配置（ALLOWED_HOSTS 已补 qhpanpan.top/www）
- [x] 6.3 生成安全 SECRET_KEY
- [x] 6.4 确保 staticfiles/ 和 media/ 目录存在且权限正确
- **实际状态**：项目已在服务器（非 git clone，可能是 tar），.env 已配置，站点可访问。✅

## 7. 后端 Docker 部署

- [x] 7.1 后端镜像已构建（rock-slab-backend 镜像存在）
- [x] 7.2 `docker compose up -d backend`，容器运行中
- [x] 7.3 数据库迁移已应用（DB 有数据）
- [x] 7.4 collectstatic（staticfiles 有内容）
- [x] 7.5 已有用户账号（13800000001 / 李一 / manager）
- [x] 7.6 `curl http://localhost:8002/api/health/` 返回 200 ✅
- **实际状态**：后端完整运行。✅

## 8. 前端构建与部署

- [x] 8.1 frontend dist 已构建
- [x] 8.2 dist/ 生成且无错误
- [x] 8.3 rock-slab-nginx 配置 root 路径与 dist 一致（挂载 /root/rock-slab/frontend/dist）
- **实际状态**：前端已部署并由 rock-slab-nginx(8080) 服务。✅

## 9. Nginx 配置与 SSL 证书签发

- [x] 9.1 新增 qhpanpan.top 虚拟主机（在 root-nginx-1 容器，保留 AI销售教练）
- [x] 9.2 证书签发（standalone 模式，非 webroot）
- [x] 9.3 HTTPS 配置生效（root-nginx-1 → 172.18.0.1:8080 → 磐盘）
- [x] 9.4 证书自动续期已配（certbot pre/post hook 停启 nginx）
- **实际状态（方式与提案不同但达成）**：未用宿主机 nginx + webroot，而是复用共享的 root-nginx-1 容器 + certbot standalone。SSL 证书已签发，HTTPS 正常。✅

## 10. 端到端验证

- [x] 10.1 HTTPS 域名访问 — https://qhpanpan.top 显示磐盘登录页 ✅
- [x] 10.2 API 健康 — `curl https://qhpanpan.top/api/health/` 返回 `{"status": "ok"}` ✅
- [ ] 10.3 验证登录功能 — **当前阻塞：浏览器登录 401（curl 正常）**
- [x] 10.4 SPA 路由 — 页面可加载
- [ ] 10.5 验证防火墙 — 外部访问 http://47.97.43.28:8080 被拒绝（**未做，8080 仍开放**）
- [x] 10.6 HTTP→HTTPS 重定向 — `curl -I http://qhpanpan.top` 返回 301 ✅
- [ ] 10.7 验证 Django admin 需认证 — 待确认（8080 暴露风险）

## 11. 部署脚本验证与收尾

- [ ] 11.1 验证 deploy.sh 一键部署可正常执行（依赖 git remote）
- [ ] 11.2 配置数据库每日备份 cron job
- [ ] 11.3 记录部署文档 — IP、域名、端口、管理账号、运维命令
