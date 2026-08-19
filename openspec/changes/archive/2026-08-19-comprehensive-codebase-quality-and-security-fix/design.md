## Context

磐盘（Rock Slab）是一个分公司行政资产盘点系统，后端 Django 5.1 + DRF，前端 Vue 3 + Element Plus，已部署到阿里云 ECS（47.97.43.28），域名 qhpanpan.top。系统已进入测试阶段，有多人同时在用。

当前状态：
- 后端 10 个 Django app，代码结构清晰，但存在安全隐患和数据模型缺陷
- 前端使用 Vue 3 Composition API + TypeScript strict mode，但视图组件过于庞大（最大 2807 行）
- 零测试覆盖（后端仅 1 个头像功能测试，前端无任何测试）
- 项目无 Git 版本控制
- 审计日志装饰器已定义但从未在业务视图上使用

## Goals / Non-Goals

**Goals:**
- 修复生产环境 SECRET_KEY 读取失败的安全隐患
- 建立密码安全和 Token 过期机制，提升系统安全基线
- 重构 Asset/Transfer 模型的分公司字段为 FK，确保数据一致性
- 激活审计日志，记录核心业务操作轨迹
- 拆分前端巨型组件，提取共享 UI 组件，提升可维护性
- 建立前后端测试框架和基础测试用例
- 初始化 Git 仓库建立版本控制

**Non-Goals:**
- Celery 异步任务队列（后续迭代）
- WebSocket 实时通知推送（后续迭代）
- API 文档（Swagger/OpenAPI）（后续迭代）
- 国际化（仅中文使用）
- CI/CD 流水线（后续迭代）
- 全面重构中文字段名为英文字段名（影响面太大，独立迭代处理）

## Decisions

### 1. SECRET_KEY 修复策略：统一为 SECRET_KEY

**决策**：修改 `rock_slab/settings/base.py` 中的 `os.environ.get('DJANGO_SECRET_KEY', ...)` 为 `os.environ.get('SECRET_KEY', ...)`，与 `.env.example` 和 `setup.sh` 保持一致。

**理由**：
- `.env.example`、`setup.sh` 和生产 `.env` 文件都使用 `SECRET_KEY` 作为变量名
- `production.py` 中已有 `ValueError` 校验确保密钥不为空
- 修改 settings 比修改所有部署脚本和 .env 文件更安全

**备选**：将所有 .env 和脚本改为 `DJANGO_SECRET_KEY` → 拒绝，因为需要修改服务器上的 .env 文件，风险更高

### 2. Token 过期方案：自定义 ExpiringToken

**决策**：创建自定义 `ExpiringToken` 模型替代 DRF 默认的 `Token`，添加 `expires_at` 字段（默认 30 天），在认证后端中检查过期。

**理由**：
- DRF 默认 Token 永不过期，存在长期泄露风险
- 自定义 Token 模型是 DRF 官方推荐方案
- 30 天过期周期适合内部系统的使用场景

**备选**：切换到 JWT（djangorestframework-simplejwt）→ 拒绝，改动面太大，当前 Token 方案够用

### 3. Asset 分公司字段重构：CharField → FK + 数据迁移

**决策**：在 `Asset` 和 `Transfer` 模型中新增 `branch` FK 字段指向 `Branch`，通过数据迁移脚本将现有字符串数据匹配到对应 Branch 记录，再删除旧的 CharField 字段。

**理由**：
- 当前 CharField 无法保证参照完整性，分支更名不会同步
- `DataScopeMixin` 中的字符串匹配 (`分公司__in=branch_names`) 可改为高效的 FK 查询
- 中文字段名暂时保留（与 Non-Goals 一致），仅新增 FK 字段

**迁移策略**：
1. 新增 `branch_id` 字段（nullable）
2. 编写 RunPython 数据迁移，按字符串匹配填充 FK
3. 验证数据完整性
4. 将字段改为 non-nullable
5. 更新序列化器和视图使用 FK 字段

### 4. 审计日志激活策略

**决策**：在以下核心操作上应用 `@audit_log` 装饰器：
- Transfer: purchase, assign, return, transfer, repair, scrap, approve
- Inventory: start, check, submit, approve, reject, cancel
- Users: create, update, delete
- Auth: login (已有 signal), password change

**理由**：
- `audit/decorators.py` 中的 `@audit_log` 已实现完整的前后快照、IP 记录、用户代理记录
- 仅需在 ViewSet 的 action 方法上添加装饰器即可
- 不影响现有功能，仅增加日志记录

### 5. 前端组件拆分策略：渐进式

**决策**：按优先级分批拆分巨型组件，优先提取重复度最高的 UI 模式为共享组件：
- 第一批：`BasePagination`、`StatusBadge`、`ImportDialog`、`FilterPanel`
- 第二批：拆分 `Organization.vue`（2807行）和 `MainLayout.vue`（1325行）
- 第三批：拆分 `Inventory.vue`、`AssetList.vue`、`Category.vue`、`Purchase.vue`

**理由**：
- 先提取共享组件，再拆分视图，避免拆分过程中重复创建相同组件
- 每批独立可交付，不影响其他批次

**备选**：一次性全部重构 → 拒绝，风险太高，难以定位回归问题

### 6. 测试框架选型

**决策**：
- 后端：pytest + pytest-django + DRF 的 APIClient，优先覆盖认证、权限、Transfer 流转、Inventory 状态机
- 前端：vitest + @vue/test-utils，优先覆盖 store 逻辑和 composables

**理由**：
- pytest 是 Django 生态标准选择，比 Django TestCase 更灵活
- vitest 是 Vite 原生测试框架，零配置集成
- 优先覆盖核心业务逻辑而非 UI 渲染，投入产出比最高

### 7. Git 初始化

**决策**：在项目根目录初始化 Git 仓库，创建 `.gitignore`（排除 node_modules、dist、.env、db.sqlite3、__pycache__、media/uploads），将当前代码作为初始提交。

**理由**：
- 当前项目无版本控制，任何误操作都无法回退
- 后续的拆分和重构必须依赖 Git 分支管理

## Risks / Trade-offs

- **[Asset FK 迁移]** 现有资产数据中的分公司名称可能与 Branch 表不匹配（拼写不一致）→ 迁移脚本中添加未匹配记录的报告，人工审核后再执行 FK 约束
- **[Token 过期]** 已登录用户的 Token 可能立即过期 → 设定 30 天宽限期，现有 Token 自动获得 expires_at = 创建时间 + 30天
- **[组件拆分]** 拆分过程中可能引入回归 bug → 每批拆分后手动测试核心功能，待测试框架就绪后增加自动化回归
- **[密码复杂度]** 现有弱密码用户（如测试账号 123456）不强制立即修改 → 仅对新密码和修改密码操作生效，现有密码在下次修改时受新规则约束
- **[性能]** Category signal 在批量导入资产时会触发 N 次 count 查询 → 使用 `transaction.atomic` 和 debounce 模式，在事务结束后统一更新计数
