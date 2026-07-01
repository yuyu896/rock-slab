# production-deploy-workflow Specification

## Purpose
TBD - created by archiving change deploy-asset-create-fix. Update Purpose after archive.
## Requirements
### Requirement: 部署提交范围控制
将代码部署到生产前，提交到 `main` 的内容 SHALL 仅包含本次目标变更的生产代码与相关 openspec 文档，SHALL NOT 包含本地 IDE/工具配置（如 `.claude/settings.local.json`）。部署前 MUST 核实本次改动不含未预期的数据库迁移文件。

#### Scenario: 提交范围排除本地配置
- **WHEN** 执行本次部署的 `git commit`
- **THEN** `.claude/settings.local.json` 不在提交内，且提交内不含 `migrations/` 下新增文件

#### Scenario: 推送前确认无未推送遗留
- **WHEN** 部署前检查 `origin/main..HEAD`
- **THEN** 本次部署提交已包含在内、无遗漏

### Requirement: 复用标准部署脚本
生产部署 SHALL 通过现网 `deploy.sh` 一次性完成，SHALL NOT 手动跳过其中备份或迁移后校验步骤。`deploy.sh` SHALL 执行：部署前数据库备份 → `git pull` → 后端 build → `migrate` → `check_seed_grants` → `collectstatic` → 前端 build → 重启后端 → nginx reload → 健康检查，并在末尾打印代码与数据回滚锚点命令。

#### Scenario: deploy.sh 全步骤通过
- **WHEN** 在服务器执行 `bash deploy.sh`
- **THEN** 9 个步骤全部成功，健康检查 `GET /api/health/` 返回 200，控制台打印部署前 commit 与备份路径作为回滚锚点

#### Scenario: 无迁移场景 migrate 为 no-op
- **WHEN** 本次为纯代码部署（无新迁移）
- **THEN** `migrate` 步骤不改变 DB schema，`check_seed_grants` 仍通过

### Requirement: 部署后针对修复点冒烟验证
健康检查通过后，SHALL 针对本次修复的具体路径在生产真实数据上验证，而非仅确认进程存活。本次 SHALL 验证：新增固定资产（仅传资产编号）成功、新增资产（不填序号）成功且序号自增/分公司正确、未在资产分类登记的资产编号被 400 拒绝。

#### Scenario: 修复路径在生产生效
- **WHEN** 部署完成后在 `qhpanpan.top` 执行三条修复路径冒烟
- **THEN** 新增固定资产/资产返回 201，未登记资产编号返回 400 且提示明确

### Requirement: 代码级回滚预案
对无迁移的纯代码部署，回滚 SHALL 仅在代码层进行（`git reset` 到部署前 commit + rebuild + 重启 + nginx reload），SHALL NOT 需要数据库恢复。`deploy.sh` 末尾 SHALL 自动给出该回滚命令。

#### Scenario: 异常时秒级代码回滚
- **WHEN** 部署后冒烟发现严重问题需要回滚
- **THEN** 执行 `deploy.sh` 末尾打印的代码回滚命令即可恢复到部署前行为，不触碰数据库

