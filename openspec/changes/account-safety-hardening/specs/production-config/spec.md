## ADDED Requirements

### Requirement: 健康端点不泄露内部异常细节

`/api/health/` 异常分支 MUST NOT 向调用方下发异常原文（数据库错误文本可能含连接目标等内部信息）：响应固定为 `{'status': 'error'}`（503），异常细节 SHALL 记录于服务端日志。该端点保持免鉴权（容器与部署脚本探活依赖）。HTTPS 强制跳转维持由外层 nginx 统一处理的既有架构（backend 层不开 SECURE_SSL_REDIRECT，避免代理链路重定向循环）。

#### Scenario: 数据库故障时健康端点不泄露

- **WHEN** 数据库不可用时请求 /api/health/
- **THEN** 返回 503 与 {'status': 'error'}，响应不含异常文本或连接信息
