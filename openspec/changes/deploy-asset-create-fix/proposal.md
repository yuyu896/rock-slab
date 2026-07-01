## Why

生产域名 `qhpanpan.top` 当前运行在上次部署的 `e43cb37`。此后本地完成了 `fix-asset-create-400` 变更——修复了用户实测报告的「新增固定资产 `POST /api/assets/fixed-assets` 返回 400」阻断 bug，并顺带修复资产新增同类 400、补齐「资产编号必须在资产分类登记」的校验。这些改动**尚未上线**，生产环境新增固定资产 / 资产仍会 400，必须部署。

本地前后端已验证通过：新增固定资产（仅传资产编号）→ 201；资产编号不存在 → 400 提示；新增资产（不填序号）→ 序号自增、分公司正确关联；未登记编号 → 400。

**数据安全**：本次为**纯后端 serializer 层改动（+53 行，零数据库迁移）**，DB schema 与上次部署完全一致，`migrate` 为 no-op，核心风险从「数据丢失」降为「新逻辑 bug」（已由 39 + 68 项测试覆盖）。

## What Changes

- **提交范围**：仅提交 `fix-asset-create-400` 成果——`backend/apps/assets/serializers.py`、两个测试文件、`openspec/changes/fix-asset-create-400/`、本部署提案目录。**不提交** `.claude/settings.local.json`（本地 IDE 配置）。
- **推送**：commit → push 到 `origin/main`。
- **服务器部署**：SSH 执行现成的 `bash deploy.sh`（备份→pull→build→migrate[本次 no-op]→check_seed_grants→collectstatic→npm build→重启→nginx reload→健康检查）。
- **部署后验证**：针对本次修复点冒烟——新增固定资产（仅资产编号）、新增资产（不填序号）、未登记资产编号被拒、资产列表/固定资产列表正常。
- **回滚预案**：无迁移，**纯代码回滚**（`git reset` 到部署前 commit + rebuild + 重启），无需数据恢复。

## Capabilities

### New Capabilities
- `production-deploy-workflow`: 将「无迁移的纯代码修复」部署到生产 `qhpanpan.top` 的标准流程——提交范围控制、复用既有 `deploy.sh`、部署后针对修复点的冒烟验证、代码级回滚。

### Modified Capabilities

## Impact

- **生产数据库**：无 schema 变更；`migrate` 为 no-op；`check_seed_grants` 仍运行（验证既有种子，应继续通过）。
- **生产代码**：`assets` app 的 `AssetSerializer` / `FixedAssetSerializer` 创建校验逻辑更新（序号自增、分公司解析、资产编号反查品目、资产编号分类登记校验）。
- **前端**：**无代码改动**；`deploy.sh` 第 7 步仍会 `npm run build`，产物与现网一致（无害）。
- **停机窗口**：仅后端容器重启 + nginx reload（秒级）；`migrate` no-op。
- **回滚**：代码回滚秒级（`deploy.sh` 末尾自动打印回滚锚点命令），无需数据恢复。
- **行为变化（预期）**：新增固定资产/资产恢复正常成功路径；未在资产分类登记的资产编号、品目表中不存在的资产编号会被 400 拒绝（这是修复的预期效果）。
- **不在范围**：不改 DB、不改前端、不改 nginx 站点/SSL、不改权限模型。
