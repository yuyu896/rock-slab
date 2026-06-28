# 生产重新部署流程（production-redeploy-workflow）

将积累的代码改动（无数据库迁移场景）重新部署到生产域名，复用既有 safe-deploy 脚本，重点在功能验证与代码回滚。

## ADDED Requirements

### Requirement: 无迁移的重新部署仍须执行部署前备份

即使本次部署无数据库迁移，部署流程 MUST 仍执行部署前即时数据库备份，并记录部署前 commit SHA，作为兜底回滚锚点。

#### Scenario: 无迁移部署前仍备份

- **WHEN** 执行一次无新迁移的生产重新部署
- **THEN** 流程 MUST 在拉取新代码前执行即时数据库备份
- **AND** MUST 记录部署前 commit SHA 并输出

### Requirement: 重新部署后必须针对本次新功能做冒烟验证

部署成功后，MUST 按本次改动涉及的功能域逐项冒烟验证，而非仅健康检查。

#### Scenario: 冒烟覆盖新功能域

- **WHEN** 本次部署含认证/并发/报表/导入/上传等改动
- **THEN** 冒烟 MUST 至少覆盖：登录限流与账号锁定、密码强度、资产导入、报表数据隔离、审批并发幂等、上传校验

### Requirement: 无迁移场景的回滚仅走代码路径

因本次无数据库迁移，回滚 MUST 仅回滚代码（git reset + 重建 + 重启），MUST NOT 触发数据库恢复。

#### Scenario: 无迁移回滚不动数据库

- **WHEN** 部署后发现功能异常且无迁移
- **THEN** 回滚 MUST 仅 `git reset` 到部署前 commit 并重建重启
- **AND** MUST NOT 执行数据库恢复操作
