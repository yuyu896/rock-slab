## ADDED Requirements

### Requirement: One-click deployment script
系统 SHALL 提供 `deploy.sh` 脚本，执行完整的部署流程：
1. 拉取最新代码（`git pull`）
2. 安装后端依赖
3. 执行数据库迁移（`python manage.py migrate`）
4. 收集静态文件（`python manage.py collectstatic`）
5. 构建前端（`npm run build`）
6. 构建 Docker 镜像并启动容器
7. 重载 Nginx 配置
8. 输出健康检查结果

#### Scenario: Full deployment
- **WHEN** 执行 `bash deploy.sh`
- **THEN** 所有步骤 SHALL 按顺序执行，任何步骤失败时 SHALL 停止并输出错误信息

#### Scenario: Deployment success output
- **WHEN** 部署成功完成
- **THEN** 脚本 SHALL 输出访问地址 `https://qhpanpan.top` 和健康检查状态

### Requirement: Environment setup script
系统 SHALL 提供 `setup.sh` 首次部署脚本，执行：
1. 创建 PostgreSQL 数据库和用户
2. 创建 `.env` 文件（交互式输入或使用默认值）
3. 初始化数据库迁移
4. 创建超级管理员账号
5. 签发 SSL 证书

#### Scenario: First-time setup
- **WHEN** 在全新服务器上执行 `bash setup.sh`
- **THEN** 所有基础设施 SHALL 就绪，系统可通过域名访问

### Requirement: Health check endpoint
后端 SHALL 提供 `/api/health/` 端点，返回系统运行状态，包含数据库连接状态。

#### Scenario: System healthy
- **WHEN** 所有服务正常运行
- **THEN** `/api/health/` SHALL 返回 HTTP 200 和 `{"status": "ok"}`

#### Scenario: Database unreachable
- **WHEN** 数据库连接失败
- **THEN** `/api/health/` SHALL 返回 HTTP 503 和 `{"status": "error", "detail": "..."}`

### Requirement: Deployment rollback
部署脚本 SHALL 支持快速回滚到上一版本。

#### Scenario: Rollback to previous version
- **WHEN** 执行 `bash deploy.sh --rollback`
- **THEN** 系统 SHALL 恢复到上一个 Git 提交版本
