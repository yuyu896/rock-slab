# frontend-error-display Specification

## Purpose
TBD - created by archiving change fix-branch-create-and-ungrouped. Update Purpose after archive.
## Requirements
### Requirement: API 错误响应可读展示

前端 MUST 对所有 API 错误展示可读信息。当后端返回非 JSON 响应（如 5xx 的 HTML 服务器错误页，`response.data` 为字符串）时，MUST NOT 逐字符显示其内容，MUST 返回包含 HTTP 状态码的通用错误提示。

#### Scenario: 后端返回 500 HTML 错误页

- **WHEN** API 返回非 JSON 响应（`response.data` 为字符串，如服务器 500 错误页）
- **THEN** 错误提示显示「服务器错误（HTTP 500），请稍后重试」等可读文案，而非逐字符乱码

#### Scenario: DRF 校验错误正常展示

- **WHEN** API 返回 DRF JSON 错误（如 `{field: [message]}`）
- **THEN** 正常提取并展示字段错误信息（不回归）

