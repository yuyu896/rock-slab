## MODIFIED Requirements

### Requirement: Production Django settings module
系统 SHALL 提供 `settings/production.py` 配置模块，继承 `settings/base.py` 并覆盖生产环境专有配置。**WSGI 生产入口（`rock_slab/wsgi.py`）的 `DJANGO_SETTINGS_MODULE` 缺省值 MUST 为 `rock_slab.settings.production`**——部署漏设环境变量时 fail-safe 到生产配置（compose 仍显式注入，双保险）。`manage.py` 为开发工具，缺省维持 development（本地 DX），两者分工须在文件内注释说明。

#### Scenario: Production settings override
- **WHEN** `DJANGO_SETTINGS_MODULE` 环境变量设为 `rock_slab.settings.production`
- **THEN** 系统使用 PostgreSQL 数据库、关闭 DEBUG、启用安全头、使用环境变量中的 SECRET_KEY

#### Scenario: WSGI 入口缺省 fail-safe
- **WHEN** 未经 compose（未设 `DJANGO_SETTINGS_MODULE`）直接以 WSGI/gunicorn 启动应用
- **THEN** 加载 production 配置而非 development

#### Scenario: manage.py 本地开发缺省不变
- **WHEN** 开发者在本地直接运行 `python manage.py <command>` 且未设环境变量
- **THEN** 使用 development 配置，本地工作流不受影响
