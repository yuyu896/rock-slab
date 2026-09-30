## ADDED Requirements

### Requirement: Audit log must not persist sensitive credential fields

审计日志的 `before_data` / `after_data` MUST NOT 含敏感凭据字段的明文或哈希值：写入路径（`audit_log` 装饰器）MUST 在序列化时将敏感键（`password` 等 `SENSITIVE_KEYS` 集合成员）的值替换为 `'***'`（保留键名以保留「字段存在/被修改」的审计事实），并 MUST 剔除 `_state` 等 Django 内部属性。存量历史记录 MUST 由数据迁移按同一脱敏规则清洗，迁移 MUST 幂等且为纯数据更新（无 DDL）。

#### Scenario: User update snapshot masks password hash
- **WHEN** 任意用户经 API 更新一个 User（触发 `@audit_log(action='update')`）
- **THEN** 生成的审计记录 `before_data` 中 `password` 值为 `'***'`，不等于库内哈希，也不含 `pbkdf2_sha256$` / `argon2` 前缀

#### Scenario: Masking applies recursively and to after_data
- **WHEN** 快照数据为嵌套结构（dict/list 多层）且某层含敏感键，或响应数据含敏感键
- **THEN** 任意层级的敏感键值均被替换为 `'***'`

#### Scenario: Backfill migration scrubs historical rows
- **WHEN** 存量 `AuditLog` 行的 `before_data` 含真实密码哈希且数据迁移执行
- **THEN** 该行 `before_data['password']` 变为 `'***'`；重复执行迁移结果不变（幂等）；其他键值不受影响

#### Scenario: Audit evidence of password change is retained
- **WHEN** 审计记录的快照中原本存在 `password` 键
- **THEN** 脱敏后该键仍存在（值为 `'***'`），审计页仍可辨识「该次更新涉及密码字段」
