## ADDED Requirements

### Requirement: Production Django settings module
系统 SHALL 提供 `settings/production.py` 配置模块，继承 `settings/base.py` 并覆盖生产环境专有配置。

#### Scenario: Production settings override
- **WHEN** `DJANGO_SETTINGS_MODULE` 环境变量设为 `rock_slab.settings.production`
- **THEN** 系统使用 PostgreSQL 数据库、关闭 DEBUG、启用安全头、使用环境变量中的 SECRET_KEY

### Requirement: Environment variable management
系统 SHALL 从 `.env` 文件读取所有环境敏感配置，包括 SECRET_KEY、DATABASE_URL、REDIS_URL、ALLOWED_HOSTS。

#### Scenario: Missing SECRET_KEY
- **WHEN** `SECRET_KEY` 环境变量未设置
- **THEN** 应用 SHALL 拒绝启动并输出明确错误信息

#### Scenario: Missing DATABASE_URL
- **WHEN** `DATABASE_URL` 环境变量未设置
- **THEN** 应用 SHALL 拒绝启动并输出明确错误信息

### Requirement: Production security headers
生产环境 SHALL 启用以下 Django 安全中间件和配置：
- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `SECURE_HSTS_SECONDS = 31536000`
- `SECURE_BROWSER_XSS_FILTER = True`
- `SECURE_CONTENT_TYPE_NOSNIFF = True`

#### Scenario: HTTP request redirect
- **WHEN** 客户端通过 HTTP 访问生产环境
- **THEN** 服务器 SHALL 返回 301 重定向到 HTTPS

#### Scenario: Cookie security
- **WHEN** 浏览器收到认证 Cookie
- **THEN** Cookie SHALL 标记为 `Secure` 和 `HttpOnly`

### Requirement: PostgreSQL database connection
生产环境 SHALL 使用 PostgreSQL 作为主数据库，通过 `dj-database-url` 解析 `DATABASE_URL` 环境变量。

#### Scenario: Database connection
- **WHEN** 应用启动并连接数据库
- **THEN** 连接参数 SHALL 从 `DATABASE_URL` 环境变量解析，包含 host、port、name、user、password

### Requirement: Redis cache backend
生产环境 SHALL 使用 Redis 作为缓存后端，通过 `CACHE_URL` 或独立环境变量配置连接。

#### Scenario: Cache key isolation
- **WHEN** 磐盘系统写入缓存
- **THEN** 所有 key SHALL 自动添加 `rock_slab:` 前缀，与同一 Redis 实例中的其他项目隔离

### Requirement: Remove hardcoded test credentials from login page
前端登录页 SHALL NOT 显示任何默认账号密码信息。

#### Scenario: Login page display
- **WHEN** 用户打开登录页面
- **THEN** 页面 SHALL NOT 包含默认账号密码提示文本
