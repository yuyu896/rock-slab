## ADDED Requirements

### Requirement: Fifth-item defect completion gate

升级准备流程 SHALL 在任何 Django 5.2 候选环境验证前确认处置清单第 5 项中的真实台账迁移缺陷已经完成独立修复、跨模块回归和验收记录。第 6 项 SHALL 记录该门槛的证据，不得在本提案中绕过、代办或仅通过修改测试隐藏该缺陷。

#### Scenario: Fifth-item defect is accepted

- **WHEN** 第 5 项真实缺陷已有修复提交、针对性回归测试和验收记录
- **THEN** 流程允许进入 Django 5.1 基线准备

#### Scenario: Fifth-item defect is incomplete

- **WHEN** 第 5 项真实缺陷仍处于待实施、待归因或待验收状态
- **THEN** 流程标记 Gate 0 阻断并停止第 6 项后续验证

### Requirement: Django 5.1 deprecation baseline

在创建或验收 Django 5.2 候选结果前，流程 SHALL 在 Django 5.1 基线环境运行项目检查和测试，清理所有由项目代码触发的 Django 弃用警告，并记录第三方依赖警告的责任包、版本和处置结论。不得存在未分类的弃用警告。

#### Scenario: Django 5.1 warnings are ready for upgrade

- **WHEN** Django 5.1 基线检查和测试完成，项目代码不再触发弃用警告，第三方警告均有责任归属和处置记录
- **THEN** 流程允许进入 Django 5.2 候选迁移和业务验证

#### Scenario: Django 5.1 warning cleanup is incomplete

- **WHEN** 项目代码仍触发弃用警告，或存在未分类的弃用警告
- **THEN** 流程停止 Django 5.2 候选验证并记录未完成原因

### Requirement: Production PostgreSQL version gate

升级准备流程 SHALL 通过只读连接核实生产 PostgreSQL 服务端版本，并将版本、连接目标、核验时间和结果摘要写入验证记录。Django 5.2 候选验证 SHALL 仅在生产版本已核实且 PostgreSQL 主版本不低于 14 时继续。

#### Scenario: PostgreSQL version meets the gate

- **WHEN** 只读核验返回 PostgreSQL 14 或更高版本
- **THEN** 流程记录服务端版本并允许进入隔离依赖和迁移验证

#### Scenario: PostgreSQL version is missing or too old

- **WHEN** 无法连接核实版本，或服务端版本低于 PostgreSQL 14
- **THEN** 流程标记为阻断并停止 Django 5.2 候选验证

### Requirement: Reproducible isolated environments

升级准备流程 SHALL 使用与 `backend/Dockerfile` 一致的 Python 3.11 基线，分别创建干净的 Django 5.1 基线环境和 Django 5.2 候选环境。两个环境 SHALL 隔离 site-packages、缓存、数据库和生成文件。候选环境可以使用未提交的临时约束覆盖安装 Django 5.2，但不得修改仓库中的 `backend/requirements.txt`。

#### Scenario: Baseline and candidate environments are created

- **WHEN** 准备流程初始化两个环境
- **THEN** 每个环境都能独立报告 Python、Django、操作系统镜像和项目提交版本

#### Scenario: Candidate environment reuses baseline packages

- **WHEN** 候选环境检测到基线环境的 site-packages 或未记录的共享依赖
- **THEN** 流程标记环境不可复现并停止验收

### Requirement: Complete production dependency installation

基线和候选环境 SHALL 按当前生产 requirements 安装完整依赖，保存安装日志和 `pip freeze`，并通过 `pip check`。流程 SHALL 验证 `dj_database_url`、`psycopg2`、`redis`、`gunicorn`、Django REST Framework、django-filter、Pillow、openpyxl 和 dotenv 可导入。

#### Scenario: Production dependencies install cleanly

- **WHEN** requirements 安装完成且 `pip check` 无冲突，关键包均可导入
- **THEN** 环境进入生产 settings 和服务启动验证

#### Scenario: Dependency installation or import fails

- **WHEN** 任一依赖无法安装、存在未满足冲突或关键包无法导入
- **THEN** 流程记录包名和错误并标记候选结果为阻断

### Requirement: Production settings and service startup verification

隔离环境 SHALL 使用 production settings 和隔离的 `SECRET_KEY`、`DATABASE_URL`、`REDIS_URL`、`ALLOWED_HOSTS` 验证 Django `check --deploy`、Gunicorn WSGI 启动、Redis 连接、collectstatic 和 `/api/health/`。生产配置验证 SHALL 不使用 dummy SQLite 数据库替代 PostgreSQL。

#### Scenario: Production runtime checks pass

- **WHEN** production settings 成功加载，Gunicorn 启动，Redis 可用，collectstatic 完成且 health 返回 200
- **THEN** 流程记录服务启动版本和检查结果并继续业务回归

#### Scenario: Production runtime check fails

- **WHEN** production settings、Gunicorn、Redis、collectstatic 或 health 任一检查失败
- **THEN** 流程停止后续候选验收并保留失败日志

### Requirement: PostgreSQL migration and application regression matrix

候选环境 SHALL 在隔离 PostgreSQL 上执行空库全量迁移、当前迁移头升级、幂等重跑、必要的回退与重放，并执行项目 PostgreSQL 并发和事务测试。候选环境还 SHALL 覆盖认证、权限和数据范围、文件上传、导入导出、资产和台账关键业务路径。

#### Scenario: Database and business matrix passes

- **WHEN** 所有迁移、回退重放、并发事务和关键业务回归均通过
- **THEN** 流程生成可供后续升级评审使用的候选验证结论

#### Scenario: Existing business defect remains unresolved

- **WHEN** 第 5 项记录的真实台账迁移缺陷尚未完成归因和处置
- **THEN** 流程将其单独列为升级阻断项，不将其归因于 Django 版本差异

### Requirement: Evidence and stop-condition record

升级准备流程 SHALL 生成一份可审查记录，至少包含环境信息、精确依赖版本、PostgreSQL 版本、执行命令、测试结果、日志位置、失败分类、重试结论、停止条件和未决问题。流程 SHALL 明确声明本次未修改版本、未连接生产执行写入、未执行部署。

#### Scenario: Readiness record is complete

- **WHEN** 隔离验证结束
- **THEN** 记录能够让评审者复现基线和候选环境，并区分通过、失败、阻断和待确认项

#### Scenario: A hard stop is triggered

- **WHEN** 任一版本、依赖、迁移、服务启动或关键业务门槛失败
- **THEN** 记录硬停止原因，流程不修改 Django 版本、不修改生产依赖约束且不执行生产部署
