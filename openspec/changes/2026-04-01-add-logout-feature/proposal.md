# 添加退出登录功能

## Why

当前系统缺少退出登录功能，用户登录后无法安全退出账号。这存在安全隐患：
- 公共电脑使用后无法清除登录状态
- 无法切换不同账号
- Token 无法主动失效

## What Changes

### 前端改动
- 在 `MainLayout.vue` 侧边栏底部的用户信息区域添加退出登录按钮
- 点击后调用 `/api/auth/logout` 接口清除服务端 Token
- 清除本地存储的 Token
- 跳转到登录页面

### 后端改动
- 后端已有 `/api/auth/logout` 接口（在 `apps/authentication/views.py` 中），无需修改

## Capabilities

### New Capabilities

- `logout-functionality`: 用户可以安全退出登录，清除客户端和服务端的认证状态

### Modified Capabilities

- `MainLayout.vue`: 在用户卡片区域添加退出按钮和交互逻辑

## Impact

### 受影响文件
- `frontend/src/layouts/MainLayout.vue` - 添加退出登录按钮和处理逻辑
- `frontend/src/layouts/MobileLayout.vue` - 移动端同样需要添加退出功能

### 受影响系统
- 用户认证流程
- 前端路由守卫

### 依赖
- 使用已有的 `logout` API
- 使用已有的路由跳转机制

### 风险
- **低风险**: 仅添加新功能，不影响现有登录流程
