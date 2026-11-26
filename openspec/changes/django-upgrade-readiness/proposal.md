## Why

处置清单第 6 项提出将项目从 Django 5.1 升级到受支持版本，当前目标候选为 Django 5.2 LTS。现有项目使用宽范围依赖约束、Docker 生产基线与本机开发环境不一致，生产 PostgreSQL 实际版本也尚未通过实时连接确认，因此直接升级会把运行时依赖、数据库兼容性和业务回归风险混在一次变更中。

本提案先建立可审查的升级前置条件和隔离验证结果，确认 PostgreSQL、生产依赖、Django 基线与候选版本均具备证据后，再单独决定是否实施版本升级。

## What Changes

- 新增 Django 升级准备流程，记录生产 PostgreSQL 的实际服务端版本，并以 Django 5.2 的 PostgreSQL 版本要求作为门槛。
- 建立与生产 Docker 基线一致的干净 Python 3.11 隔离环境，按当前生产依赖清单安装并记录解析后的完整版本、`pip check` 结果和关键包导入结果。
- 分别建立 Django 5.1 基线环境和 Django 5.2 候选环境，避免候选依赖污染当前开发环境。
- 在隔离环境中验证生产配置启动、真实 PostgreSQL 空库迁移、现有迁移头升级、`makemigrations --check`、`check --deploy`、Redis、Gunicorn、collectstatic、health 及关键业务回归路径。
- 为依赖安装失败、PostgreSQL 版本不达标、迁移失败、关键业务回归失败和生产依赖无法启动定义停止条件与记录格式。
- 将处置清单第 5 项尚未修复的真实台账迁移缺陷列为升级前置阻断项，避免把既有业务缺陷误判为 Django 升级问题。
- 将第 5 项真实缺陷的独立修复和验收设为进入本提案的 Gate 0，并在 Django 5.2 候选验证前先完成 Django 5.1 项目代码触发的弃用警告清理。
- 本提案不修改 `backend/requirements.txt` 的版本约束，不升级 Django，不修改生产数据库，不执行生产部署。

## Capabilities

### New Capabilities

- `django-upgrade-readiness`: 定义 Django 版本升级前的 PostgreSQL 版本核验、生产依赖安装、隔离环境验证、证据记录和停止条件。

### Modified Capabilities

- 无

## Impact

- 影响升级准备文档、验证脚本或隔离环境配置，以及 `backend/requirements.txt`、`backend/Dockerfile`、生产 settings、Docker Compose 和部署文档的核对流程。
- 需要访问一个与生产版本相符的 PostgreSQL 测试实例和 Redis 测试实例。生产数据库只读取版本信息，不执行迁移或写入操作。
- 需要在 Python 3.11 环境中安装当前生产依赖，并额外生成仅供验证记录使用的依赖解析清单。现有应用代码、生产依赖约束和部署入口在本提案阶段保持不变。
- 后续真正升级时，必须以本提案形成的基线、候选环境结果、迁移记录和回滚依据作为单独变更的输入。
