## Why

磐盘资产盘点系统已完成核心功能开发，需要部署到阿里云生产环境（ECS 47.97.43.28，域名 qhpanpan.top），让公司人员可以实际使用。当前系统仅在本地开发环境运行，使用 SQLite 数据库、硬编码的开发配置，存在安全隐患，不具备多人同时使用的条件。

## What Changes

- 新增后端生产环境配置（`settings/production.py`），包含 PostgreSQL 连接、Redis 缓存、安全头、HTTPS 强制跳转等
- 新增后端 Dockerfile，基于 Python 3.11 + Gunicorn 构建生产镜像
- 新增前端生产构建配置（`.env.production`），优化打包体积和加载性能
- 新增 `docker-compose.yml` 编排后端服务容器
- 新增 Nginx 站点配置，为 qhpanpan.top 提供 HTTPS 反向代理
- 新增一键部署脚本，支持代码拉取、构建、迁移、重启的自动化流程
- 配置 Let's Encrypt SSL 证书自动签发与续期
- 数据库从 SQLite 迁移到 PostgreSQL，适配生产环境
- **移除登录页硬编码的默认账号提示**（安全风险）
- 修复移动端扫描路由绕过认证的问题

## Capabilities

### New Capabilities
- `production-config`: 生产环境配置管理（Django production settings、环境变量、密钥管理）
- `docker-deployment`: Docker 容器化部署（Dockerfile、docker-compose、镜像构建）
- `nginx-reverse-proxy`: Nginx 反向代理与 HTTPS 配置（站点配置、SSL 证书、静态文件服务）
- `deploy-script`: 一键部署自动化脚本（代码更新、构建、迁移、健康检查）

### Modified Capabilities
（无需修改现有 spec 的行为要求）

## Impact

- **后端代码**：新增 `settings/production.py`、`Dockerfile`、`docker-compose.yml`、`gunicorn.conf.py`、`deploy.sh`
- **前端代码**：新增 `.env.production`，修改 `vite.config.ts` 生产构建配置，移除 `Login.vue` 默认账号提示
- **数据库**：从 SQLite 切换到 PostgreSQL，需运行所有 migration
- **依赖**：后端新增 `psycopg2-binary`、`gunicorn`，前端无新增
- **服务器**：在现有 xsjqr 项目的 Docker 环境中新增磐盘服务容器和 Nginx 站点
- **网络**：阿里云安全组需放行 qhpanpan.top 相关的 80/443 端口（已开放）
