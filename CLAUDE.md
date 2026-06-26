# Rock Slab (磐盘) — 资产管理系统

## 项目概述

企业级固定资产管理系统，面向中国市场的中小型组织，支持多级组织架构（大区→分公司→团队）的资产流转、盘点和审批流程。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11, Django 5.1, Django REST Framework |
| 前端 | Vue 3.5+ (Composition API), TypeScript 5.7, Vite 6.2+ |
| UI 库 | Element Plus (中文locale) |
| 状态管理 | Pinia 3.0 |
| 数据库 | PostgreSQL (生产), SQLite (开发/测试) |
| 缓存 | Redis (仅生产) |
| 部署 | Docker + Gunicorn + Nginx, 阿里云 |

## 项目结构

```
backend/                  # Django 后端
  apps/                   # 业务模块 (每个子目录是一个 Django app)
    authentication/       # 登录/登出、Token 认证
    users/                # 用户管理 (手机号登录)
    organizations/        # 大区、分公司、团队
    categories/           # 资产分类
    assets/               # 资产 (只读 ViewSet)
    transfers/            # 资产流转 (6种操作类型)
    inventories/          # 盘点任务 (状态机)
    reports/              # 统计报表
    notifications/        # 通知 (signal 驱动)
    audit/                # 审计日志 (@audit_log 装饰器)
  core/                   # 共享基础类 (UUIDModel, TimestampedModel, DataScopeMixin, StandardPagination)
  rock_slab/              # Django 项目配置 (base/development/production settings)
  tests/                  # pytest 测试
frontend/                 # Vue 3 前端
  src/
    api/                  # API 调用层 (每个文件对应一个后端 app)
    components/           # 可复用组件
    composables/          # 组合式函数 (useTransferList 等)
    hooks/                # 自定义 hooks (usePermission, useTable)
    constants/            # 常量定义 (角色等级、状态标签，需与后端保持一致)
    layouts/              # 布局组件 (MainLayout PC端, MobileLayout 移动端)
    router/               # 路由配置 (/ PC端, /mobile 移动端)
    store/                # Pinia stores (Composition API 风格)
    styles/               # 纯 CSS + 自定义属性 (无 Tailwind/CSS-in-JS)
    tests/                # vitest 测试
    types/                # TypeScript 类型定义
    utils/                # 工具函数 (request.ts 为 Axios 实例)
    views/                # 页面组件 (按功能分子目录)
nginx/                    # Nginx 配置 (生产反向代理)
```

## 开发命令

```bash
# 前端
cd frontend
npm run dev              # Vite 开发服务器, 端口 3000
npm run build            # 类型检查 + 构建
npm run test             # vitest
npm run test:coverage    # 带覆盖率的测试

# 后端
cd backend
pip install -r requirements.txt
python manage.py runserver              # 开发服务器
pytest                                  # 运行测试
pytest --tb=short                       # 简短回溯

# 部署 (在服务器上)
bash deploy.sh            # git pull → docker build → migrate → collectstatic → npm build → nginx reload
```

## 关键架构约定

### 后端
- **模型字段**: Django 模型使用**中文字段名** (如 `分公司`、`资产名称`、`当前状态`)，这是有意为之的设计
- **JSON 序列化**: 使用 `djangorestframework-camel-case`，后端 snake_case/中文 → 前端 camelCase
- **URL 风格**: `trailing_slash=False`, `APPEND_SLASH = False`
- **权限系统**: 5 级角色体系 admin(L1) > manager(L2) > supervisor(L3) > leader(L4) > staff(L5)
- **数据隔离**: `DataScopeMixin` 根据角色自动过滤查询集
- **所有模型**: 继承 `UUIDModel` (UUID主键) + `TimestampedModel` (created_at, updated_at)
- **认证**: 手机号+密码登录, 自定义 `ExpiringToken` (30天过期)

### 前端
- **样式**: 纯 CSS + 自定义属性，变量定义在 `styles/variables.css`，主色为暖绿色 oklch 色板，无 Tailwind
- **路径别名**: `@/*` 映射到 `./src/*`
- **API 调用**: 统一通过 `utils/request.ts` 的 Axios 实例，自动处理 401 跳转登录
- **Token 存储**: `localStorage` 中 `rock_slab_token`
- **常量同步**: `constants/index.ts` 中的角色等级必须与后端 `core/permissions.py` 保持一致
- **分页格式**: `{ count, next, previous, results }`，参数 `pageSize` (默认20, 最大100)
- **深色模式**: 通过 `prefers-color-scheme: dark` 媒体查询支持

### 资产流转 (核心业务)
6 种操作类型: purchase(采购入库), assign(领用), return(退回), transfer(调拨), repair(维修), scrap(报废)
- 每种类型有不同的审批流程和状态转换
- 资产本身不可直接修改，只能通过流转操作间接更新

### 盘点任务 (状态机)
状态: pending → in_progress → submitted → approved/rejected，通过 `TRANSITIONS` 字典管理合法转换

## 编码规范

- 后端 Python: 类/函数用英文命名，verbose_name 和展示文本用中文
- 前端 TypeScript: API 相关用英文 camelCase，与后端中文/中划线字段名对应
- 不需要写多余注释，代码应自解释
- 新功能按已有模式组织：后端 app 结构、前端 api/views/store 对应
- 测试放在对应的 tests/ 目录下

## 生产环境

- 域名: `qhpanpan.top` (HTTPS, Let's Encrypt)，服务器 47.97.43.28
- **三层架构**（详见 DEPLOYMENT.md）：`root-nginx-1`（公网 443，SSL 终止，AI 销售教练项目共享容器）→ `rock-slab-nginx`（磐盘 nginx，监听 8080，服务前端 dist + 反代 /api）→ `rock-slab-backend`（Gunicorn，8002，host 网络）
- 共享基础设施：PostgreSQL（root-db-1）、Redis（root-redis-1）容器由其他项目共享
- 线上 nginx 配置不在本仓库：root-nginx-1 用 `/root/nginx.conf`，rock-slab-nginx 用 `/root/rock-slab/nginx/rock-slab.conf`（见 nginx/README.md）
- 前端开发代理：Vite 将 `/api` 和 `/media` 代理到本地后端（开发）或生产服务器
