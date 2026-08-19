## ADDED Requirements

### Requirement: 后端 pytest 测试框架
系统 SHALL 配置 pytest + pytest-django 作为后端测试框架，使用 SQLite 内存数据库运行测试。

#### Scenario: 运行后端测试
- **WHEN** 执行 `pytest` 命令
- **THEN** 系统 SHALL 自动发现并运行所有测试用例，输出测试结果和覆盖率摘要

### Requirement: 后端认证测试
系统 SHALL 包含以下认证相关的测试用例：登录成功、登录失败（错误密码）、Token 过期、密码修改。

#### Scenario: 登录成功测试
- **WHEN** 使用正确的手机号和密码请求登录
- **THEN** 测试 SHALL 验证返回 200 和有效 Token

#### Scenario: Token 过期测试
- **WHEN** 使用已过期的 Token 请求受保护的 API
- **THEN** 测试 SHALL 验证返回 401

### Requirement: 后端权限测试
系统 SHALL 包含五级角色权限的测试用例，验证不同角色对 API 端点的访问控制。

#### Scenario: 专员无法访问管理端点
- **WHEN** 角色为 staff 的用户请求创建用户 API
- **THEN** 测试 SHALL 验证返回 403 Forbidden

#### Scenario: 数据范围隔离
- **WHEN** 专员 A 请求资产列表
- **THEN** 测试 SHALL 验证仅返回专员 A 所属分公司的资产

### Requirement: 前端 vitest 测试框架
系统 SHALL 配置 vitest + @vue/test-utils 作为前端测试框架。

#### Scenario: 运行前端测试
- **WHEN** 执行 `npm run test` 命令
- **THEN** 系统 SHALL 自动发现并运行所有测试用例

### Requirement: 前端 Store 测试
系统 SHALL 包含 Pinia store 的单元测试，覆盖用户登录登出流程和资产 CRUD 操作。

#### Scenario: 用户登录 store 测试
- **WHEN** 调用 user store 的 login action 并 mock API 返回成功
- **THEN** 测试 SHALL 验证 token 已存储、用户信息已设置、loading 状态已重置

#### Scenario: 登录失败 store 测试
- **WHEN** 调用 user store 的 login action 并 mock API 返回 401
- **THEN** 测试 SHALL 验证 error 状态已设置、token 未存储
