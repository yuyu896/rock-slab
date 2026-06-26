# 安全部署流程（safe-deploy-workflow）

涉及数据库迁移的生产部署，MUST 按"备份 → 迁移 → 验证 → 可回滚"流程执行，保证业务数据零丢失、异常可快速回退。

## ADDED Requirements

### Requirement: 涉及数据库迁移的部署前必须生成即时备份

执行 `migrate` 之前，部署流程 MUST 生成一份带时间戳的即时数据库快照（区别于每日自动备份），并记录其文件路径与部署前 commit SHA 供回滚引用。

#### Scenario: 部署前即时备份

- **WHEN** 执行涉及数据库迁移的生产部署
- **THEN** 流程 MUST 在 `git pull` / `migrate` 之前调用数据库备份
- **AND** MUST 记录备份文件路径与部署前 commit SHA 并输出

### Requirement: 迁移后必须验证种子/数据变更结果

`migrate` 完成后、服务重启前，部署流程 MUST 运行一次性校验，确认迁移的数据副作用（如种子授权）符合预期；校验失败 MUST 中止部署。

#### Scenario: 种子授权校验通过

- **WHEN** permissions 0002 种子迁移完成
- **THEN** 校验 MUST 确认 `ManagementScope` / `OperationGrant` 非空
- **AND** 抽样确认各 role 用户的授权与旧 role 隐含一致

#### Scenario: 校验失败中止部署

- **WHEN** 迁移后校验发现种子结果异常（如计数为 0 或抽样不一致）
- **THEN** 部署流程 MUST 以非零状态退出
- **AND** MUST NOT 继续执行服务重启

### Requirement: 必须提供代码回滚与数据回滚两条独立路径

部署异常时，MUST 能按问题类型选择回滚：纯前端/逻辑问题用代码回滚（不动数据库）；迁移/数据问题用数据回滚（从部署前备份恢复）。

#### Scenario: 代码回滚不动数据库

- **WHEN** 部署后出现前端或逻辑异常且数据库正常
- **THEN** 回滚 MUST 仅 `git reset` 到部署前 commit 并重建/重启服务
- **AND** MUST NOT 触发数据库恢复

#### Scenario: 数据回滚从部署前备份恢复

- **WHEN** 迁移或种子导致数据问题需要恢复
- **THEN** 回滚 MUST 停止后端、从部署前即时备份恢复数据库
- **AND** MUST 回滚代码到部署前 commit 后重启
