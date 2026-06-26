## Why

需将近几轮改动部署到生产域名 `qhpanpan.top`：白蓝配色（`frontend-blue-white-theme`）、权限解耦（`decouple-management-permissions` + `enhance-permission-assign-page`）、行政总监角色、品目/盘点页面化（`category-inventory-create-pages-and-category-perm`）。

**数据安全结论**：本次改动**不会导致数据丢失**——
- 后端仅 3 个 `permissions` 迁移（0001 建表 / 0002 种子授权 / 0003 加字段改约束），全部为**新增或种子**，不删表、不删列、不改既有业务数据；资产 / 用户 / 组织 / 流转 / 盘点等业务表结构不变。
- `role` 字段新增 `director` 选项是 CharField choices 变更，**无需迁移**，现有用户 role 值（字符串）不受影响。
- 前端改动是纯静态资源（`npm run build` 产物），由 Nginx 托管，**完全不碰数据库**。

**但存在真实风险**：现 `deploy.sh` 第 3 步直接 `migrate`，**缺少"部署前即时数据库备份"**。若 0002 种子授权在生产真实数据上行为异常（例如某用户因未命中种子而范围收窄、看不到应有数据），虽有昨日 03:07 的自动备份，但会丢失"昨日至今"的业务写入。需补齐**部署前即时备份 + 迁移后验证 + 快速回滚**三环，做到数据零丢失、问题可回退。

## What Changes

- **部署前：即时数据库备份**。在 `deploy.sh` 开头插入 `pg_dump` 即时备份步骤（复用 `/root/backup_db.sh` 或直连 PG 容器），生成带时间戳的备份文件并记录路径，确保有"部署前那一刻"的快照。
- **迁移后：种子授权验证**。`migrate` 完成后，立即校验 `ManagementScope` / `OperationGrant` 种子结果（计数 + 抽样核对 supervisor/manager/leader/staff 是否获得与旧 role 一致的授权），异常则中止部署。
- **部署后：冒烟验证清单**。健康检查之外，核对：登录、资产列表可见性、品目只读/写入口、盘点创建、权限分配页面可达。
- **回滚预案**：明确两条回滚路径——①代码回滚（`git reset` 到部署前 commit + 重新 build/重启，适用于纯前端/逻辑问题，数据库无需动）；②数据回滚（`docker compose stop backend` → 从部署前备份 `psql` 恢复 → 重启，适用于迁移/种子异常）。
- **迁移可逆性**：确认 0002（种子）的 `reverse` 已实现（清空种子数据），0003 的字段/约束变更可安全保留或回滚。

## Capabilities

### New Capabilities
- `safe-deploy-workflow`: 生产部署的"备份→迁移→验证→（回滚）"标准流程，保证部署期间业务数据零丢失、异常可快速回退。

### Modified Capabilities
<!-- 无现有 spec 涉及部署流程 -->

## Impact

- **运维脚本**：`deploy.sh` 增加"部署前备份"与"迁移后验证"两步（可选增强为独立 `deploy_safe.sh`）；不改变既有八步主流程的顺序。
- **生产数据库**：新增 `permissions_*` 两张表 + `ManagementScope.is_all_data` 字段 + 约束；种子约 N 条授权记录（N = 现有非 admin 用户数 × 其角色隐含操作 + 组织节点）。
- **生产静态资源**：前端重新 build，Nginx reload 生效。
- **停机窗口**：仅后端容器重启（秒级）+ Nginx reload；`migrate` 期间接口可能短暂报错（预计 < 30s），建议低峰执行。
- **回滚**：代码回滚秒级；数据回滚需停后端 + 恢复（约 1-3 分钟，视库大小）。
- **不在范围**：不改业务逻辑、不改 API 契约、不改组织架构；不涉及 SSL / DNS / Nginx 站点配置变更。
