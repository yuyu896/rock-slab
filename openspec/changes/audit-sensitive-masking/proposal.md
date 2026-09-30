## Why

安全审计动态复现：`audit_log` 装饰器用 `instance.__dict__` 全量序列化 `before_data`，User 更新时密码哈希（`pbkdf2_sha256$...`）原样入库；持 `view_audit` 的普通用户经审计详情接口读到的哈希与库内值**逐字相等**，可离线爆破任意账号（含 admin）。且生产审计表自上线起已积累含哈希的历史记录，仅修写入端不够，存量也要清洗。

## What Changes

- 审计装饰器序列化 `before_data` / `after_data` 时对敏感字段脱敏：`password` 一律替换为 `'***'`（保留键以示「该字段存在且被修改」），并剔除 `_state` 等 Django 内部属性
- 脱敏逻辑抽为 `apps/audit/utils.py` 的可复用纯函数，装饰器与数据迁移共用（单一事实）
- 新增数据迁移 `audit/0002`：遍历存量 `AuditLog`，对 `before_data` / `after_data` 中的敏感键值做同样脱敏（纯 DML，行级更新）
- 测试：更新用户后审计记录不含哈希、脱敏函数单测、既有审计用例回归

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `audit-log-completeness`: 新增「审计日志 MUST NOT 记录敏感凭据字段」要求（写入端脱敏 + 存量清洗）

## Impact

- `backend/apps/audit/decorators.py`：序列化处接入脱敏
- `backend/apps/audit/utils.py`：新增 `mask_sensitive(data)` 纯函数
- `backend/apps/audit/migrations/0002_*.py`：存量数据清洗（无 DDL，无新模型字段）
- `backend/tests/test_audit*.py`：新增脱敏用例
- API 行为：审计详情中 `beforeData.password` 由真实哈希变为 `'***'`（前端审计页只展示关键字段，无适配需要）
- 部署：随 migrate 自动清洗存量；`check_ledger_consistency` 与既有测试不受影响
