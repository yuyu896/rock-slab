## ADDED Requirements

### Requirement: Backend Dockerfile
系统 SHALL 提供 `backend/Dockerfile`，基于 `python:3.11-slim` 构建，包含：
- 安装系统依赖（libpq-dev 等）
- 安装 Python 依赖（requirements.txt）
- 复制应用代码
- 收集静态文件（`collectstatic`）
- 使用 Gunicorn 作为入口进程

#### Scenario: Docker image build
- **WHEN** 执行 `docker build -t rock-slab-backend .`
- **THEN** 镜像 SHALL 成功构建，包含所有 Python 依赖和应用代码

#### Scenario: Container startup
- **WHEN** 容器启动
- **THEN** Gunicorn SHALL 在 8000 端口（容器内部）监听 HTTP 请求

### Requirement: Docker compose orchestration
系统 SHALL 提供 `docker-compose.yml`，编排后端应用服务，配置：
- 从 `backend/Dockerfile` 构建
- 端口映射到宿主机 8002
- 从 `.env` 文件加载环境变量
- 挂载 media 目录为持久卷
- 连接到宿主机网络（访问已有的 PostgreSQL 和 Redis）
- 自动重启策略 `unless-stopped`

#### Scenario: Service startup
- **WHEN** 执行 `docker compose up -d`
- **THEN** 后端容器 SHALL 启动并通过 8002 端口提供 API 服务

#### Scenario: Service restart on failure
- **WHEN** 后端进程异常退出
- **THEN** Docker SHALL 自动重启容器

### Requirement: Media file persistence
系统 SHALL 将用户上传的媒体文件持久化存储在宿主机目录，通过 Docker volume 挂载。

#### Scenario: Container restart preserves uploads
- **WHEN** 容器重建或重启
- **THEN** 已上传的头像和图片文件 SHALL 保留不丢失

### Requirement: Gunicorn configuration
系统 SHALL 提供 `backend/gunicorn.conf.py`，配置：
- worker 数量：`2 * CPU核心 + 1`（2核服务器 = 5 workers）
- worker 类：`gthread`
- threads：2
- timeout：120 秒
- max-requests：1000（定期重启 worker 防止内存泄漏）
- bind：`0.0.0.0:8000`

#### Scenario: Gunicorn workers
- **WHEN** 应用启动
- **THEN** Gunicorn SHALL 启动 5 个 worker 进程处理并发请求
