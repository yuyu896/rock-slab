## Context

磐盘（Rock Slab）已上线（`qhpanpan.top`）。本次变更修复一次全面审计发现的安全与数据完整性缺陷，分布在后端 10+ 个文件、Nginx 配置和多份文档。审计证据来源：实跑 `pytest`（319 passed / 6 failed）、4 路并行代码/安全/部署审查、以及对失败测试的根因验证。

当前状态要点：
- 报表模块（`apps/reports/views.py`）用一套手写的、基于角色的硬编码作用域，与项目统一的 `DataScopeMixin + resolve_user_scope`（基于 `ManagementScope` 授权表）体系脱节。
- 口令：`UserSerializer.password` 默认 `'123456'`；`create_superuser` 默认 `admin123`；`change_password` 不调 `validate_password`。
- 导入：4 个 `import_excel` 接口对上传文件零校验；`assets/views.py` 模板生成 `Alignment(vertical='middle')` 为 openpyxl 非法值，致下载模板 500。
- 并发：`transfers.approve` 无 `transaction.atomic`；`inventories._adjust_inventory` 逐条 `save` 无 `select_for_update`。
- 限流：`REST_FRAMEWORK['NUM_PROXIES']` 未设，单层 Nginx 后所有请求共享限流桶。
- 文档：`DEPLOYMENT.md / CLAUDE.md / MAINTENANCE.md` 对 nginx 拓扑（是否三层、证书在哪终止）描述互相矛盾。

约束：生产用 PostgreSQL，开发/测试用 SQLite；生产有 Redis，开发无；中文字段名是有意设计；`trailing_slash=False`；前端 CamelCase ↔ 后端 snake_case/中文。

## Goals / Non-Goals

**Goals:**
- 消除审计列出的全部 P0 缺陷与大部分 P1 缺陷。
- 让 6 个红灯测试转绿，并补足以防回归的测试。
- 报表、口令、导入、并发、限流五类问题形成**可测试的规约**（见 specs/）。
- 统一部署文档与线上真实拓扑。

**Non-Goals:**
- 不重构中文字段名为英文（既成事实，超范围）。
- 不引入前端 `any` 类型治理、巨型组件拆分（属 P2，单独变更）。
- 不更换 Token 认证为 HttpOnly Cookie（架构级改动，超出本次）。
- 不实现"首次登录强制改密"完整状态机（本次仅清除默认弱口令；首登改密作为后续增量）。
- 不迁移大体积 xlsx 模板到 OSS（仅调整上传限制；LFS/OSS 迁移另议）。

## Decisions

### D1. 报表作用域：复用 `resolve_user_scope` 而非扩写硬编码
报表接口改为通过 `resolve_user_scope(user)` 取得该用户可见的分公司集合（与资产/盘点模块同源），再用它过滤报表 queryset。**不强制 `view_reports` 准入**：报表的越权问题是数据范围而非准入，既有产品语义是所有登录用户均可看自己范围内的统计，scope 过滤已解决；强制准入会破坏该语义（既有 `test_reports` / `test_data_scoping` 用例即按此语义编写）。
- **为何不新建独立的作用域逻辑**：项目已有成熟的 `DataScopeMixin + ManagementScope` 体系，新建逻辑必然再次漂移，正是当前 bug 的根因。
- **替代方案**：让报表 ViewSet 继承 `DataScopeMixin`。若报表是函数视图或结构不兼容，则退化为在每个接口显式调用一个 `get_scoped_branches(user)` helper。实现阶段先看 `reports/views.py` 结构二选一。

### D2. 口令：未传密码则 400，不引入随机密码 + 首登改密
移除 `UserSerializer.password` 默认值，`create_superuser` 的 `--password` 默认改为 `None` 且缺失即报错退出。
- **为何不生成随机密码 + 首登改密标记**：会引入新的模型字段、登录流程分支和测试面，与本次"清除弱口令"目标耦合过深。内部系统由管理员建号，要求显式密码最简单可控。首登改密作为后续增量（已列入 Non-Goals）。
- `change_password` 接入 `validate_password`，强度配置沿用 `base.py` 的 `MinimumLengthValidator`（建议同步把最小长度从 6 提到 8，作为本变更的一部分）。

### D3. 导入校验：抽取共享 helper，放 `core/`
新增 `core/upload_validation.py`（或挂到现有 core 模块），提供 `validate_excel_upload(file, max_size_mb, max_rows)`，统一校验扩展名/Content-Type/大小/行数。4 个 `import_excel` 接口都调用它，避免 4 处复制。
- 模板生成：`vertical='middle'` → `vertical='center'`（顺带全仓 grep 排查其他 openpyxl 样式非法值）。

### D4. 账号锁定：用 Django cache 计数，不引入 django-axes
按手机号在 Django `cache` 中累计失败次数，达阈值即写入锁定标记（带 TTL）。生产 cache backend 是 Redis，开发是 locmem，**无需新依赖、无环境差异**。
- **为何不用 django-axes**：axes 默认用 DB 记录访问日志，配置较重，且与本项目的 ExpiringToken/手机号登录模型需额外适配；本次只需"手机号失败计数 + TTL 锁定"，cache 实现足够轻量。
- `NUM_PROXIES=1` 配到 `REST_FRAMEWORK`（单层 Nginx）。

### D5. 并发：`approve` 包 atomic + 库存用 `select_for_update + F()`
- `TransferViewSet.approve` 整体 `transaction.atomic()`；审批状态写库与 `_sync_*` 在同一事务。
- `_adjust_inventory` 改 `Asset.objects.select_for_update().filter(pk=...).update(数量=F('数量')+diff)`，且整体在 `atomic` 内。
- 重复审批的幂等性：依赖现有"状态非待审批即拒绝"的守卫，事务化后该守卫在锁内判定即可（`select_for_update` 取 transfer 行）。

### D6. `director` 角色：保留并补齐（不删除）
`ROLE_LEVELS / MANAGEABLE_ROLES` 均已含 `director`，删除会牵动权限矩阵与数据；保留并在 `notifications/signals.py`（审批/抄送查询）和报表作用域中补齐 `director`。
- **替代方案（删除 director）**：影响面更大、需数据迁移，本次不采纳。若产品侧确认该角色废弃，另起变更。

### D7. 文档对齐：先核实线上，再统一三份文档
nginx 拓扑存在"单层 `qhpanpan.top.conf` 直挂"与"三层（root-nginx-1 → rock-slab-nginx → backend）"两种描述。本变更在实现阶段**先 SSH 核实线上 `root-nginx-1` 实际加载的配置**，再据实统一 `DEPLOYMENT.md / CLAUDE.md / MAINTENANCE.md`，并把仓库 `nginx/` 配置与线上对齐。

## Risks / Trade-offs

- **报表作用域收紧会缩小部分角色可见数据** → 这是预期行为，但需在发布说明告知；并提供"按授权补配 `ManagementScope`"的运维指引，避免用户感知为"数据丢了"。
- **清除默认密码后，线上仍用 `123456` 的种子账号无法登录** → 部署前用 `create_superuser`（新逻辑）或运维脚本重置；在 MAINTENANCE.md 记录该一次性动作。
- **`validate_password` 可能拒绝存量用户习惯的弱口令** → 仅作用于"修改密码"与"新建"，不强制存量改密；强度提到 8 位属温和收紧。
- **`select_for_update` 在 SQLite（开发/测试）下是 no-op** → 并发测试需用 PostgreSQL 跑，或在测试中用线程模拟并接受 SQLite 的语义限制；在测试注释说明。
- **`NUM_PROXIES=1` 若线上实际有多层代理会误判 IP** → 需在 D7 核实拓扑时一并确认代理层数，据实设置。
- **cache 锁定在 Redis 故障时退化为不限流（fail-open）** → 可接受（可用性优先于安全限速）；记录该取舍。

## Migration Plan

1. **先修无运行时风险的项**：openpyxl `vertical` 修复（D3）、报表作用域（D1）、并发（D5）—— 纯代码，随部署生效。
2. **口令与限流（D2/D4）**：改代码 + settings，部署后生效；同步在服务器重置种子账号密码。
3. **导入校验（D3）**：先调 `client_max_body_size` 与 `DATA_UPLOAD_MAX_MEMORY_SIZE`，再上接口校验。
4. **文档对齐（D7）**：核实线上后更新文档，最后 commit。
5. **回滚**：均为独立提交，可按 capability 粒度单独 `git revert`；`deploy.sh` 已有部署前备份 + 回滚锚点。

## Open Questions

- 线上 nginx 究竟是单层还是三层代理？（决定 D7 文档写法与 D4 的 `NUM_PROXIES` 取值——实现第一步需 SSH 核实）
- 仓库根目录 `资产导入模板.xlsx`（47MB）是否必须保留在 git？（若可移出，上传上限可设得更宽松；否则按 ≥47MB 设）
- 产品侧是否确认 `director` 角色仍需保留？（D6 默认保留；如废弃则另起删除变更）
