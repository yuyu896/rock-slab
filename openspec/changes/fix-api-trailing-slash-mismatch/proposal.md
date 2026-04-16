## Why

前端登录后弹出乱码错误提示，多个功能页面无法正常使用。根因是前后端 API URL 尾斜杠配置不一致：

- **后端配置**：`rock_slab/urls.py` 中所有 API 路径带尾斜杠（如 `api/assets/`），且 `APPEND_SLASH = False` 禁用了自动重定向
- **前端调用**：大部分 API 文件使用无尾斜杠路径（如 `/api/assets`）
- **结果**：请求返回 404 HTML 页面，`handleApiError()` 将 HTML 字符串当作 JSON 处理产生乱码

目前已修改 3 个 API 文件（auth.ts、regions.ts、branches.ts），但仍有 8 个 API 文件未修改，导致系统大面积功能异常。

## What Changes

- 统一所有前端 API 文件的 URL 路径，添加尾斜杠以匹配后端配置
- 受影响文件：
  - `frontend/src/api/assets.ts`
  - `frontend/src/api/users.ts`
  - `frontend/src/api/categories.ts`
  - `frontend/src/api/transfers.ts`
  - `frontend/src/api/inventories.ts`
  - `frontend/src/api/reports.ts`
  - `frontend/src/api/notifications.ts`
  - `frontend/src/api/audit.ts`

## Capabilities

### New Capabilities

无新增能力

### Modified Capabilities

- `api-consistency`: 统一前后端 API URL 格式规范，确保所有请求路径一致

## Impact

- **前端 API 层**：修改 8 个 API 文件中的所有端点 URL，添加尾斜杠
- **无后端改动**：后端配置已正确，无需修改
- **无破坏性变更**：仅修正 URL 格式，不影响接口逻辑
- **测试范围**：需验证所有 API 调用正常，包括列表、详情、创建、更新、删除操作
