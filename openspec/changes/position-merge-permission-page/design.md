## Context

- 运行时鉴权早已与 role 解耦：`User.can()` 只查 OperationGrant + admin 兜底，数据范围由 ManagementScope + 树负责人任命推导（`resolve_user_scope`）。岗位（role）只是权限分配页的**预填模板**，改岗位不改任何运行时权限。这是本案能安全合并岗位的前提。
- supervisor 退役先例（2026-08-23 permission-model-rework）：模型 choices 去 supervisor（纯 DDL migration）、前端 ROLE_LABELS 保留退役标签、存量用户走 `migrate_positions` 命令换岗（dry-run → --apply，只补不删）。staff 退役完全复用此模式。
- 权限分配页现状缺陷（v2-revision-issues.md 议题 11）：`onPickRole` 以模板整体替换勾选集，`saveRole` 按勾选集差量增删（未勾即删）→ 换岗保存会静默清除模板外单独授予的权限；保存按钮仅 `roleDirty`（岗位变化）可用，操作码增删后无保存入口。
- 生产环境真实存在 staff 用户（分公司行政），换岗必须保留其 ManagementScope（范围）与模板外授权（特例）。

## Goals / Non-Goals

**Goals:**
- 岗位体系收敛为四岗：admin / director / manager（分公司行政，8 操作码模板）/ leader（模板维持空）。
- 存量 staff 用户可经 `migrate_positions --apply` 平滑换岗为 manager，授权只补不删。
- 权限分配页：保存可用条件含操作码差集；换岗预填 = 模板 ∪ 既有授权；岗位外既有授权默认保留并提示数量。
- 前后端角色常量、页面文案与 CLAUDE.md 同步为四岗口径。

**Non-Goals:**
- 不改运行时鉴权逻辑（OperationPermission / resolve_user_scope / DataScopeMixin 一律不动）。
- 不改 OperationGrant / ManagementScope 模型结构。
- 不做 Django 数据迁移自动换岗（沿用命令 + 手动 --apply 的既有流程，规避 DDL+DML 同表迁移的 PG 陷阱）。
- leader 模板仍为空（组长价值在任命范围不在操作码，修宪记录未要求变更）。
- 不处理行政组长任命分支的创建用户入口（leader 无 manage_users 模板授权，本就不可建用户）。

## Decisions

1. **角色码保留 `manager`，staff 退役而非反向**。存量 manager 用户的授权语义 ⊆ 新模板（8 操作码覆盖原 5 项），迁移方向 staff→manager 只需补授；反向则要把 manager 用户降级解释。`LEGACY_POSITION_MAP` 增 `'staff': 'manager'`，命令代码零改动。
2. **模型 choices 去 staff + 默认 role 改 `manager`，一个纯 DDL migration（users.0008）**。不掺 DML——同迁移内对 users 表 UPDATE 会触发 PG pending trigger events 陷阱（项目已有两次踩坑记录）。存量换岗由命令承担。
3. **`MANAGEABLE_ROLES` 收敛为四岗**：admin→[admin,director,manager,leader]、director→[manager,leader]、manager→[manager,leader]（分公司行政互建账号——原"manager 建 staff"语义在合并后的等价物；新号无任何授权与数据范围，扩权风险由 admin-only 的权限分配页把关）、leader→[]。删除 perform_create 中"leader 只能建 staff"块（staff 不可分配后为死代码，权线校验已覆盖）。
4. **权限页保存语义 = "勾选集即目标态"，但预填集改为并集**。`saveRole` 的差量对齐逻辑（增缺删多）保持不变——它本身就是"显式取消勾选才删除"的实现；缺陷根源在 `onPickRole` 的整体替换。改为 `draftOps = template ∪ existing` 后，默认保存只增不删，与命令原则一致。admin 用户操作码区禁用（内置全部）维持现状。
5. **脏检查**：`canSave = 岗位变化 || draftOps 与既有授权码集存在差集`。用 grants 的码集（非 OperationGrant 对象 id）比对，避免分页/排序噪音。
6. **保留提示**：换岗选中模板后，若 `既有授权 ∖ 模板 ≠ ∅`，在操作码区下方提示"将保留岗位外的既有授权 N 项（显式取消勾选才删除）"。N 按当前勾选集与模板差集实时计算，取消勾选即从保留数中移除。
7. **前端角色文案单一事实源**：MainLayout / mobile Home / mobile Profile 的三份本地 roleLabels 映射改为统一引用 `constants` 的 `ROLE_LABELS`（每样信息只存一处）；`ROLE_LEVELS` 收敛为 admin1/director2/manager3/leader4，supervisor/staff 置于 5/6 仅作存量排序展示。
8. **`check_seed_grants` 增存量退役岗位 WARN**（不 fail）：存在 role ∈ {supervisor, staff} 的活跃用户时提示运行 `migrate_positions --apply`。leader/staff 分公司授权校验循环改为仅 leader。

## Risks / Trade-offs

- [部署后忘记跑 `migrate_positions --apply`，存量 staff 长期挂在退役岗位] → check_seed_grants 每次部署 WARN 提示；staff 用户功能不受影响（授权表驱动），仅岗位标签显示"已退役"。
- [migrate_positions 对存量 manager 也补授 8 操作码，等于全员扩权（含审批）] → 设计定案接受："2 人分公司自查自批属可接受治理成本"；模板外低频操作（dispose_assets 等）仍走单独授予，命令只补不删、不越模板。
- [前端 staff 选项从表单移除后，编辑存量 staff 用户时下拉无当前值] → 保留"已退役"disabled 选项兜底展示（Organization.vue 员工表单对存量 staff/ supervisor 动态追加退役选项）。
- [conftest 存量 staff fixture 与新四岗口径不一致] → 保留 fixture 为 staff（作为"存量未换岗用户不炸"的回归面），新增测试覆盖换岗后形态；注释说明意图。

## Migration Plan

1. 合并代码 → 部署（`bash deploy.sh`：自动跑 users.0008 DDL migration + check_seed_grants WARN 提示存量 staff）。
2. 服务器执行 `docker compose run --rm backend python manage.py migrate_positions`（dry-run）核对逐人清单（重点：staff→manager 人数、补授操作码数）。
3. 确认无误后 `--apply` 执行；再次 dry-run 应显示"无变化"。
4. 回滚：代码回滚到部署前 commit 即可；已换岗的用户角色/授权为增量写入（只补不删），如需精确还原用部署前备份（deploy.sh 第 1 步自动备份）。
