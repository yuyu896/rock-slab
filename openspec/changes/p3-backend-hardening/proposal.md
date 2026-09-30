## Why

安全审计 P3 两条收尾：① Django Admin 以裸 ModelAdmin 注册 User——admin 表单可直接写 password 列（无校验、绕过一切流程）、停用用户不联动 `is_active`、不清理 token（动态复现确认），是 API 路径外的旁路写入口。生产已实证无公网入口（域名回退 SPA、8002 不通公网，仅 SSH 隧道可达），属纵深防御缺陷。② `wsgi.py` 的 `DJANGO_SETTINGS_MODULE` 缺省为 development——漏设环境变量时生产入口（gunicorn/WSGI）会以开发配置启动（宽松 HOSTS、调试行为）。manage.py 是开发工具、缺省 development 属刻意 DX，不在本列。

## What Changes

- Django Admin **反注册 User**：用户管理唯一入口为 API（人员管理，含权线闸/审计/token 联动）；admin 站点保留其余模型的只读排障用途。运维需改用户时走 `manage.py shell`（留 shell 历史）
- `wsgi.py` 缺省改为 `rock_slab.settings.production`：WSGI 生产入口在漏设环境变量时 fail-safe 到生产配置（compose 仍显式注入，双保险）；`manage.py` 维持 development 缺省并注释说明分工
- pytest 不受影响（pytest.ini 自带 DJANGO_SETTINGS_MODULE）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `account-lifecycle-security`: 新增「Django Admin MUST NOT 暴露用户模型编辑」要求
- `production-config`: 「Production Django settings module」要求补齐 wsgi 入口缺省口径

## Impact

- `backend/apps/users/admin.py`：反注册 User（模块保留说明注释）
- `backend/rock_slab/wsgi.py`：setdefault 改 production
- `backend/manage.py`：注释说明与 wsgi 的分工（不改默认值）
- 测试：新增「admin 站点无 User 注册」用例；全量回归
- 无迁移；无前端改动
