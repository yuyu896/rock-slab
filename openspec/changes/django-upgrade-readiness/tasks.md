## 0. 第五项完成门槛

- [ ] 0.1 确认处置清单第 5 项真实台账迁移缺陷已有独立修复、跨模块回归测试和验收记录
- [ ] 0.2 第 5 项未完成或证据不完整时记录 Gate 0 阻断，并停止第 6 项后续工作，不在本提案中代办第 5 项

## 1. Django 5.1 基线和弃用警告

- [ ] 1.1 按 `backend/Dockerfile` 创建干净的 Python 3.11 Django 5.1 基线环境
- [ ] 1.2 在 Django 5.1 基线环境安装当前生产依赖，记录 Python、Django、依赖解析结果和项目提交版本
- [ ] 1.3 使用 `check`、`check --deploy`、测试套件和运行时入口收集 Django 弃用警告
- [ ] 1.4 清理所有由项目代码触发的 Django 弃用警告，保留第三方依赖警告的责任包、版本和处置结论
- [ ] 1.5 重新运行基线检查和测试，确认没有未分类的弃用警告，未通过时停止第 6 项候选验证

## 2. PostgreSQL 版本和隔离资源

- [ ] 2.1 使用只读连接执行 `SHOW server_version` 或 `SELECT version()`，记录生产 PostgreSQL 实际版本、连接目标、核验时间和结果摘要
- [ ] 2.2 核对 PostgreSQL 版本是否满足 Django 5.2 的最低要求，未核实或低于要求时记录阻断并停止候选验证
- [ ] 2.3 准备与生产主版本相符的隔离 PostgreSQL、隔离 Redis、独立数据库、独立缓存和独立生成文件目录
- [ ] 2.4 确认隔离资源不指向生产写入目标，测试结束后销毁临时资源

## 3. Django 5.2 候选环境和完整生产依赖

- [ ] 3.1 创建独立的 Django 5.2 候选环境，隔离 site-packages、pip 缓存、数据库、Redis 和生成文件
- [ ] 3.2 使用未提交的临时约束覆盖安装 Django 5.2 目标补丁版本和同一生产依赖集合，不修改仓库中的 `backend/requirements.txt`
- [ ] 3.3 保存安装日志和 `pip freeze`，在基线与候选环境运行 `pip check`
- [ ] 3.4 验证 `dj_database_url`、`psycopg2`、`redis`、`gunicorn`、DRF、django-filter、Pillow、openpyxl 和 dotenv 可导入
- [ ] 3.5 确认候选环境未复用基线 site-packages，并记录精确版本和镜像信息

## 4. 生产配置和部署启动验证

- [ ] 4.1 为隔离环境准备独立 SECRET_KEY、DATABASE_URL、REDIS_URL 和 ALLOWED_HOSTS
- [ ] 4.2 在 Django 5.2 候选环境运行 `python manage.py check --deploy`、`makemigrations --check --dry-run` 和普通 `check`
- [ ] 4.3 使用隔离 PostgreSQL 执行 production settings 启动检查和数据库连接检查
- [ ] 4.4 使用隔离 Redis 验证缓存连接、键前缀和基础读写
- [ ] 4.5 执行 collectstatic，启动项目 Gunicorn WSGI 入口并验证 `/api/health/` 返回 200

## 5. Django 5.2 数据库和业务回归

- [ ] 5.1 在与生产主版本相符的隔离 PostgreSQL 空库执行全量 `migrate`
- [ ] 5.2 从当前迁移头执行升级、幂等重跑，以及可逆迁移所需的回退与重放并保存日志
- [ ] 5.3 运行项目已有的 PostgreSQL 并发、事务和锁行为测试，单独记录 SQLite 与 PostgreSQL 的差异
- [ ] 5.4 运行认证、权限和数据范围、文件上传、导入导出、资产和台账关键业务回归
- [ ] 5.5 对所有失败按依赖、环境、数据库、框架兼容性或既有业务缺陷分类，避免将第 5 项缺陷归因于 Django

## 6. 结论和后续变更边界

- [ ] 6.1 生成升级准备记录，包含精确版本、命令、日志位置、通过项、失败项、阻断项、待确认问题和重试结论
- [ ] 6.2 对 PostgreSQL 版本、依赖安装、Django 5.1 弃用警告、迁移、服务启动或关键业务任一硬门槛失败，停止并记录不可升级结论
- [ ] 6.3 对全部门槛通过的结果提出单独的 Django 版本升级变更建议，附基线、候选环境和回滚依据
- [ ] 6.4 确认本提案实施期间未修改 Django 版本、requirements 约束、生产数据库、生产配置和部署结果
