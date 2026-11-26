## Context

当前 `backend/requirements.txt` 将 Django 约束在 `>=5.1,<5.2`，而 `backend/Dockerfile` 使用 Python 3.11 slim 作为生产镜像。生产配置通过 `dj-database-url` 读取 `DATABASE_URL`，通过 psycopg2 连接 PostgreSQL，并通过 Redis 后端和 Gunicorn 提供运行时能力。requirements 中的多个第三方依赖只有下限或宽范围，没有完整锁定文件，因此本机已经安装的包不能代表生产解析结果。

部署文档记录生产 PostgreSQL 镜像为 `pgvector:pg16`，但该记录不能替代实时服务端版本。Django 5.2 候选环境还必须验证真实 PostgreSQL、Redis、生产 settings、容器入口和关键业务路径。处置清单第 5 项记录的真实台账迁移缺陷需要先单独处理，否则升级验证结果无法归因。

## Goals / Non-Goals

**Goals:**

- 先确认处置清单第 5 项真实台账缺陷已经独立修复并通过验收，再开始本提案的升级准备工作。
- 以只读方式核实生产 PostgreSQL 的 `server_version`，并把实际版本、核验时间和连接目标写入验证记录。
- 使用 Python 3.11 建立干净的基线环境和候选环境，分别保存 Django 5.1 与 Django 5.2 的完整依赖解析结果。
- 在 Django 5.1 基线上清理项目代码触发的 Django 弃用警告，形成稳定的升级前基线。
- 在隔离 PostgreSQL 和 Redis 实例上验证生产依赖安装、应用启动、迁移、静态文件、健康检查、Gunicorn 和关键业务回归。
- 输出可审查的通过、失败、阻断和待确认结论，为后续独立升级变更提供输入。

**Non-Goals:**

- 不修改 `requirements.txt`、Django 版本、业务代码、生产 settings 或部署脚本。
- 不在生产数据库执行迁移、写入、回滚、清理或升级操作。
- 不把本地 SQLite 测试通过当作 PostgreSQL 兼容性证明。
- 不在本提案中决定生产发布时间、执行发布或恢复生产数据库。

## Decisions

### 1. 以生产 Docker 基线作为验证基线

隔离环境固定使用 Python 3.11，与 `backend/Dockerfile` 一致。候选验证优先复制 Docker 构建链路和完整 requirements 安装过程。使用任意本机全局环境作为验证环境会掩盖缺失依赖和版本漂移，因此只把本机环境用于诊断，不作为验收证据。

### 2. 生产 PostgreSQL 版本采用实时只读核验

在获得只读连接后执行 `SHOW server_version` 或 `SELECT version()`，记录服务端版本、连接目标、核验时间和命令结果摘要。版本门槛按 Django 5.2 要求设置为 PostgreSQL 14 或更高，并优先使用与生产实际主版本相同的隔离测试实例。部署文档中的 `pgvector:pg16` 仅作为待核对线索。

### 3. 保留 Django 5.1 基线和 Django 5.2 候选两个独立环境

基线环境按当前约束安装并运行现有测试和运行时检查。候选环境在独立目录、虚拟环境或容器镜像中安装 Django 5.2 的最新补丁版本，并记录精确版本。候选环境不得复用基线环境的 site-packages、缓存数据库或已生成的迁移状态。

候选环境使用临时的、未提交的约束覆盖或临时 requirements 副本，将 Django 约束改为目标 5.2 补丁范围，同时保留其余项目依赖约束。仓库中的 `backend/requirements.txt` 在本提案阶段不改动，候选环境的临时文件和解析结果必须单独归档。

### 4. 生产依赖采用完整解析和运行时探针双重验证

两个环境都执行 `pip install -r requirements.txt`、`pip freeze` 和 `pip check`。验证至少包括 `dj_database_url`、`psycopg2`、`redis`、`gunicorn`、Django REST Framework、django-filter、Pillow、openpyxl 和 dotenv 的导入。Gunicorn 必须使用项目 WSGI 入口启动并通过隔离健康检查，不能只验证命令存在。

### 5. 数据库验证分为结构迁移和业务回归

在隔离 PostgreSQL 上分别执行空库全量迁移、从当前迁移头启动、`migrate` 幂等重跑、必要的回退与重放，以及项目已有的 PostgreSQL 并发和事务测试。随后使用 production settings 验证认证、权限和数据范围、文件上传、导入导出、资产和台账关键路径。SQLite 测试结果只作为应用层补充证据。

### 6. 用明确门槛阻止候选结果误报为可升级

以下任一情况发生时，候选结果标记为阻断并停止后续升级建议。生产 PostgreSQL 版本无法核实或低于 14，依赖无法完整安装或 `pip check` 失败，生产 settings 无法启动，真实 PostgreSQL 迁移失败，Gunicorn、Redis 或 health 失败，关键业务回归失败，或第 5 项真实台账缺陷尚未完成归因和处置。失败记录包含环境、命令、日志摘要、影响范围和重试结论。

### 7. 回滚依据只用于后续升级变更

本提案只准备代码回滚点、镜像标识、依赖解析清单和数据库备份检查项，不执行回滚。未来真正升级时，代码回滚和数据库恢复必须单独决策，不能把候选验证环境的回退操作误当作生产恢复。

## Risks / Trade-offs

- [生产 PostgreSQL 版本暂时无法连接核实] → 将版本核验设为硬门槛，未核实前不输出可升级结论。
- [宽范围依赖导致每次解析结果不同] → 在基线和候选环境保存 `pip freeze`、Python 版本、镜像摘要和安装日志。
- [候选环境通过但真实业务缺陷仍存在] → 将第 5 项台账缺陷作为独立阻断项，按失败分类记录，不归因给 Django。
- [仅使用 SQLite 会漏掉 PostgreSQL 行为差异] → 把真实 PostgreSQL 迁移、并发、事务和关键回归列为必测项。
- [生产 settings 依赖缺失环境变量或外部服务] → 使用隔离的 PostgreSQL、Redis、SECRET_KEY 和 DATABASE_URL，禁止以 dummy SQLite 结果替代生产配置验证。

## Migration Plan

本提案阶段按以下顺序实施。先确认第 5 项真实缺陷已独立修复并验收，再建立 Django 5.1 基线并清理项目代码触发的弃用警告。随后核实生产 PostgreSQL 版本，创建基线和候选隔离环境，安装并锁存依赖，完成运行时探针和数据库迁移，最后执行业务回归并生成结论。任何硬门槛失败都停止，不进入版本修改或部署。所有测试使用隔离数据库和 Redis，测试结束后销毁临时资源。

## Open Questions

- 生产 PostgreSQL 的实时 `server_version` 和完整镜像摘要尚待只读核验。
- 生产 Redis 的连接地址、认证方式和可用隔离实例尚待确认。
- Django 5.2 候选的具体补丁版本在执行准备流程时按当时可用的受支持补丁版本确定并记录。
- Django 5.1 运行中出现的第三方依赖弃用警告需要单独记录责任包和处置结论，不能将其与项目代码警告混为一项。
