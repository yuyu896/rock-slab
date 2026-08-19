## Why

一次全面代码与安全审计在已上线的磐盘系统中发现若干**会直接造成数据错账、越权访问或服务不可用**的缺陷：固定资产导入模板生成在服务端 500 崩溃、6 个后端测试红灯未被 CI 拦截、报表模块绕过统一权限体系导致越权读全公司数据、新建/超管账号默认弱口令、导入接口对上传文件零校验（可被 ZIP 炸弹打挂），且部署文档与线上 nginx 拓扑互相矛盾。这些问题现在就应修，因为它们要么已在影响真实功能，要么是潜伏的安全红线。

## What Changes

**P0 — 必须修复（数据/安全/可用性）**

- 修复固定资产导入模板生成崩溃：`openpyxl` `Alignment(vertical='middle')` 为非法值，改为 `vertical='center'`，恢复"下载导入模板"接口并连带修复 4 个失败测试。
- 报表模块回归统一授权：5 个报表接口改用 `resolve_user_scope` 过滤查询集（与 `DataScopeMixin` 同源），消除无授权 `manager` 越权看全公司数据；报表保持对所有登录用户可见（既有产品语义），仅按管理授权范围隔离数据。
- 清除弱口令体系：移除 `UserSerializer` 默认密码 `'123456'`、`create_superuser` 默认 `admin123`（改为强制传参/环境变量）；`change_password` 接入 `django.contrib.auth.password_validation.validate_password`。
- 导入接口加文件校验：`assets / categories / transfers / inventories` 的 `import_excel` 统一校验扩展名、Content-Type、文件大小、最大行数，防 ZIP 炸弹与超时 DoS。
- **BREAKING**（仅文档层）：统一部署架构描述，消除 `DEPLOYMENT.md / CLAUDE.md / MAINTENANCE.md` 与线上 nginx 拓扑的矛盾；上调 `client_max_body_size` 以容纳实际导入模板体积。

**P1 — 应修复（健壮性/一致性）**

- 流转审批与盘点并发安全：`transfers.approve` 整体包 `transaction.atomic()`；库存调整改用 `select_for_update().filter().update(数量=F('数量')+diff)` 批量加锁更新。
- `director` 角色全链路一致（**决策：保留 `director` 并补齐**，因 `ROLE_LEVELS / MANAGEABLE_ROLES` 已含此角色，删除影响面更大）：通知审批/抄送、报表作用域补齐 `director`。
- 登录限流真正生效：配置 `REST_FRAMEWORK['NUM_PROXIES']=1`（单层 nginx），并增加按手机号的失败计数 + 临时锁定。
- 让 6 个失败测试转绿（密码测试改 `format='json'` 触发 CamelCase 解析；4 个导入测试随 P0 修复转绿）。

## Capabilities

### New Capabilities

- `report-data-scoping`: 报表查询集必须遵循统一数据范围授权，且覆盖全部已定义角色（含 `director`），不再使用手写硬编码作用域。
- `password-security`: 口令生命周期安全——禁止默认弱口令、创建超管强制显式凭据、修改密码走 Django 密码校验器。
- `file-import-validation`: 所有 Excel 导入接口对上传文件做类型/大小/行数校验；导入模板生成必须可成功导出。
- `inventory-concurrency-control`: 流转审批与盘点库存调整在并发下保证一致（事务 + 行锁 + 幂等）。
- `auth-throttling`: 登录限流按真实客户端 IP 生效，并对单账号暴力破解做锁定。

### Modified Capabilities

（无。现有 `openspec/specs/` 下的 spec 均为归档占位，无实际 Requirements 需修改。）

## Impact

- **后端代码**：`apps/reports/views.py`、`apps/users/{serializers,views}.py`、`apps/authentication/{views,throttling}.py`、`core/management/commands/create_superuser.py`、`apps/assets/views.py`、`apps/categories/views.py`、`apps/transfers/views.py`、`apps/inventories/views.py`、`apps/notifications/signals.py`、`rock_slab/settings/base.py`。
- **配置**：`nginx/qhpanpan.top.conf`（`client_max_body_size`）；`settings` 的 `REST_FRAMEWORK`、`DATA_UPLOAD_MAX_MEMORY_SIZE`。
- **文档**：`DEPLOYMENT.md / CLAUDE.md / MAINTENANCE.md / TESTING.md`（架构拓扑一致化、移除仓库内真实凭据）。
- **测试**：修复 `tests/test_auth.py`、`test_rbac_matrix.py`、`test_fixed_asset.py`、`test_import_export.py` 的 6 个失败用例；新增覆盖报表越权、口令校验、导入校验、并发审批的回归测试。
- **依赖**：可能新增 `django-axes` 或等价的轻量账号锁定实现（待 design 决策）。
- **运行时风险**：清除默认密码后，旧种子账号若仍用 `123456` 需运维侧重置；报表作用域收紧后，部分角色可见数据范围会缩小（预期行为）。
