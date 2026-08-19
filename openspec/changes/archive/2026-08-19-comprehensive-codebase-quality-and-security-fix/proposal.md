## Why

磐盘系统已上线运行，但经过全面代码审计，发现多项影响系统安全性和可维护性的问题：SECRET_KEY 环境变量名不匹配可能导致生产环境故障、零测试覆盖使迭代充满风险、Asset/Transfer 模型缺少外键约束导致数据不一致、审计日志装饰器定义但未使用、前端多个视图组件超过 1300 行难以维护。这些问题需要在正式推广使用前修复，以保障系统长期稳定运行。

## What Changes

- **修复 SECRET_KEY 环境变量名不匹配**：统一 `base.py` 和 `.env.example` 中的环境变量名为 `SECRET_KEY`
- **补全登录验证**：让登录视图使用已定义的 `LoginSerializer`，移除死代码
- **增强密码安全**：添加密码复杂度验证、Token 过期机制、修改密码后轮换 Token
- **添加登录限流**：为登录端点增加独立的防暴力破解限流
- **修复 Asset/Transfer 模型**：将分公司字段从 CharField 改为指向 Branch 的 FK，确保数据一致性
- **激活审计日志**：在核心业务视图（创建/审批/删除）上应用 `@audit_log` 装饰器
- **修复 Category 计数器**：通过 Django signal 自动维护 `asset_count` 和 `in_stock_count`
- **拆分前端巨型组件**：将 6 个超过 1000 行的视图组件拆分为子组件和 composables
- **提取共享 UI 组件**：将重复的分页、表格、弹窗、状态徽章等抽取为公共组件
- **统一错误处理**：前端添加全局错误边界，统一 store 错误处理模式
- **添加基础测试框架**：后端 pytest + 前端 vitest，覆盖核心业务逻辑
- **初始化 Git 仓库**：建立版本控制

## Capabilities

### New Capabilities
- `secret-key-fix`: 修复生产环境 SECRET_KEY 环境变量名不匹配问题，确保 Django 能正确读取 .env 中的密钥
- `password-and-token-security`: 密码复杂度验证、Token 过期与轮换机制，防止弱密码和 Token 泄露
- `login-brute-force-protection`: 登录端点独立限流，防止暴力破解攻击
- `asset-foreign-key-refactor`: Asset/Transfer 模型的分公司字段从 CharField 重构为 FK，并完成数据迁移
- `audit-log-activation`: 在核心业务视图上激活 @audit_log 装饰器，记录完整的操作审计轨迹
- `category-counter-signal`: 通过 Django post_save/post_delete signal 自动维护 Category 的资产计数
- `shared-ui-components`: 提取前端共享 UI 组件（分页、表格、弹窗、状态徽章、筛选面板）
- `frontend-error-boundary`: Vue 全局错误边界 + 统一 store 错误处理模式
- `test-framework-setup`: 前后端测试框架搭建及核心业务逻辑测试用例

### Modified Capabilities
（无需修改现有 spec 的行为要求，本次变更均为修复和增强，不改变功能规格）

## Impact

- **后端模型**：`Asset` 和 `Transfer` 模型的分公司字段类型变更，需要数据库迁移（**BREAKING** — 需先迁移已有字符串数据到 FK）
- **后端视图**：登录视图改用 LoginSerializer；核心视图添加 @audit_log 装饰器
- **后端安全**：新增密码验证器、Token 过期机制，现有用户首次修改密码时受新规则约束
- **后端 signals**：新增 Category 计数器维护信号，影响资产创建/删除/更新时的写入性能
- **前端组件**：6 个巨型视图组件拆分，不影响功能但文件结构大幅变化
- **前端新增**：~10 个共享 UI 组件、全局错误处理
- **依赖新增**：后端 pytest + pytest-django，前端 vitest + @vue/test-utils
- **Git**：项目根目录初始化 Git 仓库，添加 .gitignore
