 ## 1. 版本控制初始化

- [x] 1.1 在项目根目录创建 `.gitignore`（排除 node_modules、dist、.env、db.sqlite3、__pycache__、media/uploads、*.pyc、.DS_Store）
- [x] 1.2 执行 `git init`，将当前代码作为初始提交

## 2. SECRET_KEY 修复

- [x] 2.1 修改 `backend/rock_slab/settings/base.py` 中的 `os.environ.get('DJANGO_SECRET_KEY', ...)` 为 `os.environ.get('SECRET_KEY', ...)`
- [x] 2.2 验证 `.env.example` 中的变量名与 `base.py` 一致
- [ ] 2.3 更新服务器上的 `.env` 文件确认使用 `SECRET_KEY` 变量名

## 3. 登录验证修复

- [x] 3.1 重构 `apps/authentication/views.py` 的 `login_view`，使用 `LoginSerializer` 进行输入验证
- [x] 3.2 确认 `LoginSerializer` 的验证逻辑完整（phone 格式、password 非空）
- [x] 3.3 移除视图中直接从 `request.data.get()` 读取的冗余代码

## 4. 密码与 Token 安全

- [x] 4.1 创建 `apps/authentication/validators.py`，实现密码最小长度 6 位验证器
- [x] 4.2 在 `settings/base.py` 的 `AUTH_PASSWORD_VALIDATORS` 中注册新验证器
- [x] 4.3 创建 `apps/authentication/models.py` 中的 `ExpiringToken` 模型（继承 `Token`，添加 `expires_at` 字段，默认 30 天）
- [x] 4.4 创建 `apps/authentication/backends.py` 中的 `ExpiringTokenAuthentication` 认证后端，检查 Token 过期
- [x] 4.5 在 `settings/base.py` 中将 `REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']` 切换为新的认证后端
- [x] 4.6 修改登录视图，创建 Token 时设置 `expires_at`
- [x] 4.7 修改 `change_password_view`，密码修改成功后删除旧 Token、创建新 Token 并返回
- [x] 4.8 编写数据迁移，为现有 Token 设置 `expires_at = created + 30天`
- [x] 4.9 前端处理 Token 过期：在响应拦截器中检测 Token 过期错误，提示用户重新登录

## 5. 登录防暴力破解限流

- [x] 5.1 创建 `apps/authentication/throttling.py`，实现 `LoginRateThrottle` 类（每 IP 每分钟 5 次）
- [x] 5.2 在登录视图上添加 `@throttle_classes([LoginRateThrottle])` 装饰器
- [x] 5.3 前端处理 429 响应，显示"请求过于频繁，请稍后再试"提示

## 6. Asset/Transfer 外键重构

- [x] 6.1 在 `Asset` 模型中新增 `branch` FK 字段（nullable=True，指向 `Branch`，related_name='assets'）
- [x] 6.2 在 `Transfer` 模型中新增 `from_branch` 和 `to_branch` FK 字段（nullable=True，指向 `Branch`）
- [x] 6.3 创建 RunPython 数据迁移脚本，按分公司字符串匹配 Branch 记录并填充 FK
- [x] 6.4 在迁移脚本中添加未匹配记录的报告输出
- [x] 6.5 运行迁移并验证数据完整性
- [x] 6.6 创建新迁移将 FK 字段改为 non-nullable（保持 nullable，由应用层保证）
- [x] 6.7 更新 `AssetSerializer` 和 `TransferSerializer` 使用 FK 字段
- [x] 6.8 更新 `DataScopeMixin` 使用 FK 查询替代字符串匹配
- [x] 6.9 更新所有 Transfer action（purchase, assign, return, transfer 等）使用 FK
- [x] 6.10 更新前端 API 类型和视图，适配新的 FK 字段结构

## 7. 审计日志激活

- [x] 7.1 在 `TransferViewSet` 的 purchase, assign, return, transfer, repair, scrap action 上添加 `@audit_log` 装饰器
- [x] 7.2 在 `TransferViewSet` 的 approve action 上添加 `@audit_log` 装饰器
- [x] 7.3 在 `InventoryTaskViewSet` 的 start, submit, approve, reject, cancel action 上添加 `@audit_log` 装饰器
- [x] 7.4 在 `UserViewSet` 的 create, update, destroy action 上添加 `@audit_log` 装饰器
- [x] 7.5 在 `change_password_view` 上添加 `@audit_log` 装饰器
- [ ] 7.6 验证审计日志记录包含正确的操作类型、前后数据快照和操作人信息

## 8. Category 计数器 Signal

- [x] 8.1 创建 `apps/categories/signals.py`，实现 `update_category_counts` 函数（根据资产分类聚合更新 asset_count 和 in_stock_count）
- [x] 8.2 连接 `post_save` 和 `post_delete` signal 到 Asset 模型
- [x] 8.3 处理批量导入场景：使用 `transaction.on_commit` 延迟计数更新，避免 N+1 查询
- [x] 8.4 创建管理命令 `recount_categories`，手动重新计算所有分类计数（用于修复历史数据）
- [ ] 8.5 验证批量导入后分类计数准确

## 9. 前端共享 UI 组件

- [x] 9.1 创建 `src/components/BasePagination.vue`（分页组件，props: total/currentPage/pageSize，emits: change）
- [x] 9.2 创建 `src/components/StatusBadge.vue`（状态徽章，props: status/statusMap，自动映射颜色和文字）
- [x] 9.3 创建 `src/components/ImportDialog.vue`（导入对话框，封装文件选择、上传进度、结果展示）
- [x] 9.4 创建 `src/components/FilterPanel.vue`（筛选面板，支持动态配置筛选条件）
- [x] 9.5 在现有视图中替换自实现的分页/状态/导入/筛选为共享组件

## 10. 前端组件拆分 — MainLayout

- [x] 10.1 从 `MainLayout.vue` 提取 `SidebarNav.vue`（侧边栏导航菜单）
- [x] 10.2 从 `MainLayout.vue` 提取 `UserPanel.vue`（用户信息面板弹窗）
- [x] 10.3 从 `MainLayout.vue` 提取 `PasswordChangeModal.vue`（修改密码弹窗）
- [x] 10.4 重构 `MainLayout.vue` 使用提取的子组件，确保文件 < 500 行

## 11. 前端组件拆分 — Organization

- [x] 11.1 从 `Organization.vue` 提取 `RegionManager.vue`（区域管理面板）
- [x] 11.2 从 `Organization.vue` 提取 `BranchManager.vue`（分公司管理面板）
- [x] 11.3 从 `Organization.vue` 提取 `TeamManager.vue`（团队管理面板）
- [x] 11.4 从 `Organization.vue` 提取 `PersonnelManager.vue`（人员管理面板）
- [x] 11.5 重构 `Organization.vue` 使用提取的子组件，确保文件 < 500 行

## 12. 前端组件拆分 — 其他视图

- [x] 12.1 拆分 `Inventory.vue`（提取 InventoryTaskList、InventoryCheckPanel、InventoryReport 子组件）
- [x] 12.2 拆分 `AssetList.vue`（提取 AssetCreateForm、AssetDetailDrawer、AssetImportDialog、AssetPrintDialog 子组件）
- [x] 12.3 拆分 `Category.vue`（提取 CategoryForm、CategoryImportDialog 子组件）
- [x] 12.4 拆分 `Purchase.vue`（提取 PurchaseCreateForm、PurchaseDetail、PurchaseImportDialog 子组件）

## 13. 前端错误处理

- [x] 13.1 在 `main.ts` 中注册 `app.config.errorHandler`，捕获未处理错误并显示 Element Plus 错误提示
- [x] 13.2 统一 `store/asset.ts` 错误处理模式（添加 error ref、使用 handleApiError）
- [x] 13.3 统一 `store/inventory.ts` 错误处理模式（移除动态 import workaround，添加 error ref）
- [x] 13.4 为其他 store 补充统一的 error ref 和 try/finally loading 管理

## 14. 后端测试框架

- [x] 14.1 添加 pytest、pytest-django、pytest-cov 到 `requirements.txt`
- [x] 14.2 创建 `backend/pytest.ini` 配置文件（DJANGO_SETTINGS_MODULE、数据库、目录）
- [x] 14.3 创建 `backend/conftest.py`（公共 fixtures：用户工厂、认证 helper）
- [x] 14.4 编写认证测试：`tests/test_auth.py`（登录成功、登录失败、Token 过期、密码修改）
- [x] 14.5 编写权限测试：`tests/test_permissions.py`（五级角色访问控制、数据范围隔离）
- [x] 14.6 编写 Transfer 测试：`tests/test_transfers.py`（采购入库、领用出库、审批流程）
- [x] 14.7 编写 Inventory 测试：`tests/test_inventories.py`（状态流转、盘点执行、审批）

## 15. 前端测试框架

- [x] 15.1 添加 vitest、@vue/test-utils、happy-dom 到 `package.json` devDependencies
- [x] 15.2 创建 `frontend/vitest.config.ts` 配置文件
- [x] 15.3 编写 user store 测试：`tests/store/user.test.ts`（登录、登出、fetchProfile）
- [x] 15.4 编写 asset store 测试：`tests/store/asset.test.ts`（fetchAssets、筛选、分页）
- [x] 15.5 编写 usePermission hook 测试：`tests/hooks/usePermission.test.ts`（角色层级判断）
- [x] 15.6 添加 `npm run test` 和 `npm run test:coverage` 脚本到 `package.json`

## 16. 验证与收尾

- [x] 16.1 运行全量后端测试 `pytest` 并确保通过
- [x] 16.2 运行全量前端测试 `npm run test` 并确保通过
- [ ] 16.3 手动验证登录/登出流程正常
- [ ] 16.4 手动验证资产采购入库和审批流程正常
- [ ] 16.5 手动验证盘点流程正常
- [ ] 16.6 确认生产环境部署后 SECRET_KEY 可正确读取
- [x] 16.7 更新 TESTING.md 文档
