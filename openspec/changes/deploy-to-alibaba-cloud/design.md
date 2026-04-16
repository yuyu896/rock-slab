## Context

磐盘（Rock Slab）是一个分公司行政资产盘点系统，后端 Django + DRF，前端 Vue 3 + Element Plus。目前仅本地开发运行（SQLite + runserver），需部署到阿里云 ECS 上供公司全员使用。

目标服务器（47.97.43.28）已运行 xsjqr 项目，共用 Docker 环境中已有的 PostgreSQL 16 和 Redis 7。域名 qhpanpan.top 已准备。

当前状态：
- 后端：SQLite 数据库，DEBUG=True，开发密钥，无 HTTPS
- 前端：Vite dev server，硬编码 localhost API 地址，登录页显示默认账号
- 部署：无 Dockerfile、无 docker-compose、无 Nginx 配置、无 CI/CD

## Goals / Non-Goals

**Goals:**
- 磐盘系统通过 https://qhpanpan.top 对外提供稳定访问
- 支持多人同时使用（PostgreSQL 替代 SQLite）
- 自动化 HTTPS（Let's Encrypt 自动签发与续期）
- 一键部署/更新流程（git pull → build → restart）
- 与现有 xsjqr 项目互不影响，共用基础设施

**Non-Goals:**
- CI/CD 流水线（后续迭代再做）
- Kubernetes / 容器编排（单体容器足够）
- 自动化测试体系（不在本次部署范围内）
- 国际化（仅中文使用）

## Decisions

### 1. 容器化方案：独立 docker-compose

**决策**：磐盘使用独立的 `docker-compose.yml`，仅包含后端应用容器。PostgreSQL 和 Redis 复用 xsjqr 已有的 Docker 服务。

**理由**：
- 避免重复部署数据库和缓存，节省服务器资源
- 磐盘与 xsjqr 通过不同的数据库名隔离，互不影响
- 独立 compose 文件便于后续迁移到其他服务器

**备选**：合并到 xsjqr 的 docker-compose 中 → 拒绝，因为耦合度高，迁移不便

### 2. Web 服务器：Gunicorn + Nginx

**决策**：后端用 Gunicorn（4 worker）作为 WSGI 服务器，前端构建为静态文件，统一由现有 Nginx 反向代理。

**理由**：
- Gunicorn 是 Django 生产部署的标准方案，稳定可靠
- 前端静态文件直接由 Nginx 提供，性能最优
- Nginx 处理 HTTPS 终止、压缩、缓存，减轻应用层负担

**架构**：
```
客户端 → Nginx (443/HTTPS)
              ├── qhpanpan.top → 前端静态文件 (/)
              ├── qhpanpan.top/api → Gunicorn 后端 (8002)
              └── qhpanpan.top/media → 媒体文件目录
```

### 3. 后端端口：8002

**决策**：磐盘后端容器映射到宿主机 8002 端口。

**理由**：8000 已被 xsjqr 占用，8001 已被 AI 服务占用，选 8002 无冲突。

### 4. 数据库：在现有 PostgreSQL 中新建数据库

**决策**：在现有 PostgreSQL 16 实例中创建 `rock_slab` 数据库，专用账号 `rock_slab_user`。

**理由**：
- 复用已有服务，无需额外部署
- 数据库级别隔离，权限可控
- 备份可独立进行

**连接信息**：
- Host: `root-db-1`（Docker 内部网络）或 `localhost:5432`（宿主机）
- Database: `rock_slab`
- User: `rock_slab_user`

### 5. Redis：共用，使用 key 前缀

**决策**：共用 Redis 实例，Django 配置 `CACHE_KEY_PREFIX = 'rock_slab:'`。

**理由**：磐盘缓存需求低，无需独立 Redis 实例。

### 6. HTTPS：Let's Encrypt + certbot

**决策**：使用 certbot 自动签发 Let's Encrypt 证书，配置 Nginx 自动续期。

**理由**：免费、自动、被业界广泛使用。

### 7. 环境变量管理：.env 文件

**决策**：在项目根目录使用 `.env` 文件管理所有环境相关配置，不提交到 Git。

**理由**：简单直观，docker-compose 原生支持 `.env` 文件加载。

### 8. 目录结构

```
/root/rock-slab/              # 服务器上的项目根目录
├── docker-compose.yml        # 后端服务编排
├── .env                      # 环境变量（不入 Git）
├── deploy.sh                 # 一键部署脚本
├── backend/                  # Django 后端代码
│   ├── Dockerfile
│   ├── gunicorn.conf.py
│   ├── requirements.txt
│   └── ...
├── frontend/                 # Vue 前端代码
│   ├── dist/                 # 构建产物
│   └── ...
└── nginx/                    # Nginx 配置
    └── qhpanpan.top.conf
```

## Risks / Trade-offs

- **[共用数据库]** 如果 PostgreSQL 容器重启或故障，两个项目同时受影响 → 定期备份，后续可迁移到独立 RDS
- **[端口冲突]** 后续其他服务可能需要 8002 → 可随时在 .env 中修改端口
- **[无 CDN]** 静态文件直接从 ECS 提供，全国访问速度取决于单台服务器带宽 → 初期用户量少可接受，后续可接入阿里云 CDN
- **[SQLite → PostgreSQL 迁移]** 数据库引擎切换可能暴露 ORM 兼容性问题 → 在开发环境先用 PostgreSQL 测试，确保 migration 全部通过后再部署
- **[安全组]** 服务器已有 80/443 端口开放，但需确认阿里云安全组规则允许 HTTP/HTTPS 入站 → 部署前验证
