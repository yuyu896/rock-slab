## ADDED Requirements

### Requirement: 受信任反向代理保留外部请求协议

公网 Nginx MUST 根据客户端与公网入口之间的实际连接协议设置 `X-Forwarded-Proto`。受信任的内层应用代理 MUST 将该协议值转发给 Django，MUST NOT 用内层代理自己的连接 scheme 覆盖它。公网入口 MUST 覆盖客户端自行提供的 `X-Forwarded-Proto`，Django MUST 仅信任配置的代理协议头。

#### Scenario: HTTPS 图片 URL 保持安全协议
- **WHEN** 用户通过 HTTPS 请求实例档案 API，且 Django 为图片字段生成绝对 URL
- **THEN** API 返回的主图与缩略图 URL 均使用 HTTPS

#### Scenario: HTTP 请求按入口协议处理
- **WHEN** 请求经公网入口以 HTTP 到达且由入口重定向至 HTTPS
- **THEN** 入口不会把未经验证的客户端协议头作为可信值转发，重定向后的 API 图片 URL 使用 HTTPS
