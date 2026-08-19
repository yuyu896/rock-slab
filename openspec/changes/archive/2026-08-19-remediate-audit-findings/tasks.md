## 1. 先决条件与现状核实

- [ ] 1.1 SSH 登录生产服务器，核实 `root-nginx-1` 实际加载的配置：磐盘是"单层 `qhpanpan.top.conf` 直挂 443"还是"三层（root-nginx-1 → rock-slab-nginx → backend）"。记录结论。
- [ ] 1.2 确认 Nginx 到后端的代理层数，确定 `NUM_PROXIES` 取值（预期为 1）。
- [ ] 1.3 确认线上是否仍存在用 `123456` / `admin123` 的种子账号，列出需重置的账号清单。
- [ ] 1.4 阅读 `apps/reports/views.py` 结构（函数视图 vs ViewSet），确定 D1 的接入方式（继承 `DataScopeMixin` 还是显式 `get_scoped_branches` helper）。

## 2. P0 — 固定资产导入模板修复（file-import-validation）

- [ ] 2.1 修复 `apps/assets/views.py` 模板生成处 `Alignment(vertical='middle')` → `vertical='center'`。
- [ ] 2.2 全仓 grep `vertical=` / `Alignment(` 排查其他 openpyxl 样式非法值，一并修正。
- [ ] 2.3 跑 `pytest tests/test_import_export.py tests/test_fixed_asset.py`，确认 4 个导入相关失败用例转绿。

## 3. P0 — 报表越权修复（report-data-scoping）

- [ ] 3.1 在 `apps/reports/views.py` 引入 `resolve_user_scope(user)`，用返回的 Branch 查询集过滤所有 5 个报表接口的 queryset，移除手写硬编码作用域（`_scope_asset_queryset` / `_scope_transfer_queryset` 等）。
- [x] 3.2 （决策调整）**不强制 `view_reports` 准入**——报表对所有登录用户可见，仅按 `resolve_user_scope` 做数据范围隔离（与既有 `test_reports`/`test_data_scoping` 语义一致；强制准入会破坏产品语义）。
- [ ] 3.3 在报表作用域中正确处理 `director` 角色（按其 `ManagementScope` 授权范围，MUST NOT 降级为普通 staff）。
- [ ] 3.4 新增 `tests/test_reports.py` 用例：无授权 manager 看不到全公司数据、supervisor 仅看授权大区、缺 `view_reports` 返回 403、director 按授权范围返回。

## 4. P0 — 口令安全（password-security）

- [ ] 4.1 移除 `apps/users/serializers.py` 中 `UserSerializer.password` 的默认值 `'123456'`；未传密码时返回 400（不创建账号）。
- [ ] 4.2 `core/management/commands/create_superuser.py`：`--password` 默认改为 `None`，缺失则打印错误并以非零状态码退出；`--phone` 同样要求显式提供。
- [ ] 4.3 `apps/authentication/views.py` 的 `change_password`：调用 `validate_password(new_password, user=user)`，校验失败返回 400 且不修改密码。
- [ ] 4.4 将 `base.py` `MinimumLengthValidator` 最小长度由 6 提升到 8（与本变更一同收紧）。
- [ ] 4.5 收紧 `change_password` 与 `logout` 里裸 `except Exception: pass`，改为捕获具体异常并 `logger.warning`。
- [ ] 4.6 新增/补充测试：未传密码建号失败、`create_superuser` 无密码报错退出、改密弱口令被拒、改密成功用例改用 `format='json'` 触发 CamelCase 解析。

## 5. P0 — 导入文件校验与上传限制（file-import-validation）

- [ ] 5.1 新增 `core/upload_validation.py`，实现 `validate_excel_upload(file, max_size_mb, max_rows)`：校验扩展名 `.xlsx`、Content-Type、大小、行数。
- [ ] 5.2 在 `assets / categories / transfers / inventories` 四处 `import_excel` 接口调用该校验，校验失败返回 400 且不进入 `load_workbook`。
- [ ] 5.3 调整 `nginx/qhpanpan.top.conf` 的 `client_max_body_size`（≥ 实际最大模板体积，结合 1.4 结论，如 60M）。
- [ ] 5.4 在 `production.py` 显式设置 `DATA_UPLOAD_MAX_MEMORY_SIZE` / `FILE_UPLOAD_MAX_MEMORY_SIZE` 与 nginx 一致。
- [ ] 5.5 新增测试：上传非 xlsx / 超大 / 超行数文件均返回 400 且不触发解析。

## 6. P0 — 部署文档对齐（无 spec，纯文档）

- [ ] 6.1 依据 1.1 / 1.2 核实结论，统一 `DEPLOYMENT.md` 的架构描述（层数、证书终止点、端口）。
- [ ] 6.2 同步更新 `CLAUDE.md` 与 `MAINTENANCE.md` 中关于 nginx/部署架构的段落，消除三份文档矛盾。
- [ ] 6.3 确保仓库 `nginx/` 配置与线上实际生效配置一致。
- [ ] 6.4 从 `TESTING.md` 移除真实手机号与明文密码，改为占位符或说明（真实凭据不进公开仓库）。

## 7. P1 — 并发安全（inventory-concurrency-control）

- [ ] 7.1 `apps/transfers/views.py` 的 `approve`（及同类审批动作）整体包 `transaction.atomic()`；审批状态写库与资产同步在同一事务。
- [ ] 7.2 `approve` 内对 transfer 行用 `select_for_update` 取得后再判定状态，保证重复/并发审批的幂等。
- [ ] 7.3 `apps/inventories/views.py` 的 `_adjust_inventory` 改为 `select_for_update().filter(pk=...).update(数量=F('数量')+diff)`，整体在 `atomic` 内。
- [ ] 7.4 排查并修复"序号/内部编号"用 `count()+1` 生成导致的并发重复（加锁计数或数据库约束）。
- [ ] 7.5 新增并发回归测试（PostgreSQL 下）：盘点与采购入库并发不丢失更新、重复审批只同步一次、序号不冲突；在 SQLite 下跑的部分注明语义限制。

## 8. P1 — 登录限流与账号锁定（auth-throttling）

- [ ] 8.1 在 `REST_FRAMEWORK` 设置 `NUM_PROXICES`（按 1.2 结论，预期 `1`）。
- [ ] 8.2 实现按手机号的失败计数 + TTL 锁定（基于 Django `cache`）：窗口内失败达阈值则锁定，锁定期间即使密码正确也返回锁定提示，成功登录清零计数。
- [ ] 8.3 在 `apps/authentication/views.py` 登录失败路径接入计数与锁定检查。
- [ ] 8.4 确保生产（Redis）与开发（locmem）cache backend 均可用；记录 Redis 故障时 fail-open 的取舍。
- [ ] 8.5 新增测试：不同 IP 独立计数、同手机号达阈值锁定、锁定窗口内拒绝正确密码、成功登录清零。

## 9. P1 — director 角色通知链路补齐

- [ ] 9.1 `apps/notifications/signals.py` 审批人/抄送人查询补齐 `director`（当前仅查 `['admin','manager','supervisor']`）。
- [ ] 9.2 审查 `get_approvers_for_branch` 等忽略入参/全量通知的隐患，按授权范围收敛（参考 design D6）。
- [ ] 9.3 新增/补充通知测试：director 用户能收到其授权范围内的待审批/抄送通知。

## 10. 全量验收

- [ ] 10.1 `pytest --tb=short` 全绿，确认原 6 个失败用例 + 本次新增用例全部通过，无新增失败。
- [ ] 10.2 前端 `npm run build`（vue-tsc + vite）通过。
- [ ] 10.3 在 staging/本地用真实 xlsx 走通"下载模板 → 填写 → 导入"完整链路。
- [ ] 10.4 人工核验报表作用域：用一个无授权 manager 账号确认看不到全公司数据。
- [ ] 10.5 更新 MAINTENANCE.md 记录本次一次性运维动作（重置种子账号密码、`NUM_PROXIES` 取值依据、上传上限新值）。
- [ ] 10.6 `openspec status --change remediate-audit-findings` 确认全部任务完成，准备归档。
