## 1. 后端生产环境配置

- [x] 1.1 添加生产依赖到 requirements.txt（`psycopg2-binary`、`gunicorn`、`dj-database-url`、`redis`）
- [x] 1.2 创建 `backend/rock_slab/settings/production.py`，配置 PostgreSQL、Redis、安全头、DEBUG=False
- [x] 1.3 创建 `backend/gunicorn.conf.py` Gunicorn 配置文件
- [x] 1.4 创建 `backend/.env.example` 环境变量模板
- [x] 1.5 修改 `backend/manage.py` 支持 `DJANGO_SETTINGS_MODULE` 环境变量切换

## 2. 前端生产构建配置

- [x] 2.1 创建 `frontend/.env.production` 配置生产 API 地址
- [x] 2.2 优化 `frontend/vite.config.ts`（代码分割、构建配置、路径别名修复）
- [x] 2.3 移除 `frontend/src/views/Login.vue` 中硬编码的默认账号密码提示
- [x] 2.4 修复移动端 `/mobile/scan/:taskId` 路由缺少 `requiresAuth` 的问题

## 3. Docker 容器化

- [x] 3.1 创建 `backend/Dockerfile`（Python 3.11-slim + Gunicorn）
- [x] 3.2 创建项目根目录 `docker-compose.yml`（后端服务 + Nginx + volume 挂载 + 环境变量）
- [x] 3.3 创建 `.dockerignore` 文件排除不必要的文件

## 4. Nginx 配置

- [x] 4.1 创建 Nginx 站点配置（反向代理 + 静态文件 + gzip）
- [x] 4.2 配置 Let's Encrypt SSL 证书签发（待域名备案后执行）
- [x] 4.3 配置 HTTP 到 HTTPS 301 重定向（待域名备案后执行）
- [x] 4.4 配置 gzip 压缩和静态文件缓存头
- [x] 4.5 部署 Nginx 容器（独立 rock-slab-nginx 容器，端口 8080）

## 5. 服务器初始化

- [x] 5.1 在服务器上创建项目目录 `/root/rock-slab/`
- [x] 5.2 在现有 PostgreSQL 中创建 `rock_slab` 数据库和 `rock_slab_user` 用户
- [x] 5.3 创建服务器 `.env` 文件（配置 SECRET_KEY、DATABASE_URL、REDIS_URL、ALLOWED_HOSTS）
- [x] 5.4 将代码上传到服务器（scp）
- [x] 5.5 执行数据库迁移 `python manage.py migrate`
- [x] 5.6 收集静态文件（Docker 构建时执行）
- [x] 5.7 构建前端 `npm run build`（本地构建后 scp 上传）
- [x] 5.8 构建 Docker 镜像并启动后端容器

## 6. 部署脚本

- [x] 6.1 创建 `deploy.sh` 一键部署/更新脚本
- [x] 6.2 创建 `setup.sh` 首次部署初始化脚本
- [x] 6.3 添加 `/api/health/` 健康检查端点到后端

## 7. 验证与收尾

- [x] 7.1 验证 http://47.97.43.28:8080 可正常访问
- [x] 7.2 验证登录功能正常（超级管理员 13800000000 登录成功）
- [ ] 7.3 验证移动端页面可正常使用
- [ ] 7.4 验证数据库备份脚本可正常工作
- [x] 7.5 更新 `TESTING.md` 中的访问地址和测试账号信息
