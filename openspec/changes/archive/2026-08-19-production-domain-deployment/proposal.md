## Why

磐盘（Rock Slab）已完成核心功能开发，需要部署到已备案域名 qhpanpan.top（阿里云 ECS 47.97.43.28）正式上线使用。当前服务器已部分就绪但无法通过域名正常访问，且代码库存在若干部署阻塞项，必须先修复代码并重新配置服务器才能完成上线。

**服务器现状**（2026-06-14 实测）：
- 后端 API 在 `47.97.43.28:8080` 正常运行（`/api/health/` 返回 200 `{"status": "ok"}`）
- 域名 DNS 已生效：`qhpanpan.top` 和 `www.qhpanpan.top` 均解析到 47.97.43.28
- Nginx 在 443 端口监听，但通过域名访问 `https://qhpanpan.top` 时 **SSL 握手失败**（curl 退出码 35）；通过 IP 加 `-k` 可得 200，说明证书未正确签发或与域名不匹配
- 后端 8080 端口直接暴露公网（Django admin 可外部访问），存在安全隐患

**代码层面阻塞问题**（实测确认）：
- **未提交的迁移文件**：assets(0004/0005)、organizations(0004)、transfers(0006/0007) 共 5 个迁移文件未被 git 跟踪。deploy.sh 通过 `git pull` 部署，这些文件不会进入服务器，导致代码与数据库 schema 不一致
- **CSRF_TRUSTED_ORIGINS 缺失**：production.py 未定义，配合 `CSRF_COOKIE_SECURE=True`，所有 POST/PUT/DELETE 请求会 403
- **PORT 冲突**：gunicorn.conf.py 绑定 `0.0.0.0:{PORT}`，.env 设 PORT=8002，但 docker-compose 健康检查和容器实际监听端口不一致（host 网络模式下端口映射失效）
- **无 git remote**：本地仓库没有远程仓库，deploy.sh 的 `git pull origin main` 无法执行
- **无 entrypoint/migrate 步骤**：Dockerfile 直接 CMD gunicorn，容器重启不会自动迁移

## What Changes

### 代码修复（部署前置阻塞项）

- **提交未跟踪迁移文件**: `git add` 5 个迁移文件（assets 0004/0005、organizations 0004、transfers 0006/0007）
- **添加 CSRF_TRUSTED_ORIGINS**: production.py 中加入 `['https://qhpanpan.top', 'https://www.qhpanpan.top']`
- **统一端口**: 解决 gunicorn PORT 绑定（8002）与健康检查端口的冲突
- **添加 entrypoint.sh**: 容器启动前自动执行 `migrate`，Dockerfile 设为 ENTRYPOINT
- **补全 ALLOWED_HOSTS**: 加入 `www.qhpanpan.top`

### 配置 Git 远程仓库

- 创建远程仓库（GitHub/Gitee/阿里云 Codeup），配置 origin，推送全部代码（含迁移文件）

### 服务器配置与部署

- 安装 PostgreSQL + Redis（如未安装）
- 防火墙仅开放 22/80/443，关闭 8080 外部访问
- clone 项目到 /root/rock-slab/，创建生产 .env
- Docker 构建后端、运行迁移、collectstatic
- 前端 npm build
- **新增**磐盘 Nginx 虚拟主机（保留 AI销售教练项目不变，通过 server_name 区分）
- **修复/签发 SSL 证书**（当前域名 HTTPS 握手失败）—— Let's Encrypt certbot
- 修正 deploy.sh 的 Nginx reload 命令（`root-nginx-1` → 宿主机命令）
- 端到端验证

## Capabilities

### New Capabilities
- `commit-pending-migrations`: 提交未跟踪的数据库迁移文件，确保部署时 schema 与代码一致
- `code-fixes-for-deploy`: 后端代码修复（CSRF_TRUSTED_ORIGINS、PORT 统一、entrypoint、ALLOWED_HOSTS）
- `git-remote-setup`: 配置 git 远程仓库以支持服务器 git pull 部署
- `server-infrastructure`: 服务器基础环境（PostgreSQL、Redis、防火墙）
- `docker-backend-deployment`: Docker 容器化后端部署（构建、迁移、collectstatic、运行）
- `frontend-build-deploy`: 前端构建产物与 Nginx 静态服务
- `nginx-ssl-setup`: Nginx 虚拟主机配置与 SSL 证书签发（修复当前证书问题）
- `deploy-pipeline`: deploy.sh 脚本修正与一键部署验证

### Modified Capabilities

（无已有 capability 需要修改）

## Impact

- **未提交迁移文件（5 个）**: 必须先 git add + commit，否则部署后数据库 schema 不一致（BLOCKING）
- **backend/rock_slab/settings/production.py**: 添加 CSRF_TRUSTED_ORIGINS，补全 ALLOWED_HOSTS
- **backend/gunicorn.conf.py 或 docker-compose.yml**: 统一 PORT 与健康检查端口
- **backend/entrypoint.sh（新建）/ backend/Dockerfile**: 启动前自动 migrate
- **deploy.sh**: 修正 Nginx reload 命令
- **nginx/qhpanpan.top.conf**: 已有模板，部署为新增虚拟主机
- **服务器**: 新增磐盘 vhost + 签发 SSL 证书（当前证书损坏）+ 防火墙关闭 8080
- **git remote**: 需新建远程仓库并推送
- **DNS**: ✅ 已生效，无需改动
- **前端**: ✅ 当前可正常构建（vue-tsc 0 错误，Transfer 类型已补全）
