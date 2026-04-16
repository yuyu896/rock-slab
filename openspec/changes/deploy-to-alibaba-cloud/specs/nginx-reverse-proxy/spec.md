## ADDED Requirements

### Requirement: Nginx site configuration for qhpanpan.top
系统 SHALL 提供 Nginx server block 配置文件，处理 `qhpanpan.top` 域名的请求：
- `/` → 前端静态文件（`/root/rock-slab/frontend/dist/`）
- `/api/` → 反向代理到后端 Gunicorn（`127.0.0.1:8002`）
- `/media/` → 媒体文件目录（`/root/rock-slab/backend/media/`）
- `/static/` → 后端收集的静态文件（`/root/rock-slab/backend/staticfiles/`）

#### Scenario: Frontend access
- **WHEN** 用户访问 `https://qhpanpan.top/`
- **THEN** Nginx SHALL 返回前端构建的 `index.html`

#### Scenario: API proxy
- **WHEN** 用户请求 `https://qhpanpan.top/api/assets/`
- **THEN** Nginx SHALL 反向代理到后端 Gunicorn 的 `http://127.0.0.1:8002/api/assets/`

#### Scenario: Media files
- **WHEN** 用户请求 `https://qhpanpan.top/media/avatars/xxx.jpg`
- **THEN** Nginx SHALL 直接返回媒体目录中的文件

### Requirement: HTTPS with Let's Encrypt
系统 SHALL 使用 Let's Encrypt 签发的 SSL 证书，配置 HTTPS：
- 证书自动签发（certbot）
- HTTP 到 HTTPS 自动重定向（301）
- SSL 协议：TLSv1.2、TLSv1.3
- HSTS 头：max-age=31536000

#### Scenario: HTTPS access
- **WHEN** 用户访问 `https://qhpanpan.top`
- **THEN** 连接 SHALL 使用有效的 SSL 证书加密

#### Scenario: HTTP redirect
- **WHEN** 用户访问 `http://qhpanpan.top`
- **THEN** Nginx SHALL 返回 301 重定向到 `https://qhpanpan.top`

### Requirement: Nginx performance optimization
Nginx 配置 SHALL 包含以下性能优化：
- gzip 压缩（text/css、application/javascript、application/json）
- 静态文件缓存头（CSS/JS 缓存 30 天，图片缓存 7 天）
- 客户端上传文件大小限制 20MB

#### Scenario: Static file caching
- **WHEN** Nginx 返回 `.css` 或 `.js` 文件
- **THEN** 响应头 SHALL 包含 `Cache-Control: public, max-age=2592000`

#### Scenario: Gzip compression
- **WHEN** 客户端发送支持 gzip 的请求头
- **THEN** Nginx SHALL 压缩文本类响应

### Requirement: Nginx integration with existing setup
磐盘的 Nginx 配置 SHALL 以独立配置文件形式添加到现有 Nginx 容器中，不修改 xsjqr 的配置。

#### Scenario: Coexistence with xsjqr
- **WHEN** Nginx 同时加载 xsjqr 和磐盘的配置
- **THEN** 两个项目 SHALL 各自通过域名独立访问，互不影响
