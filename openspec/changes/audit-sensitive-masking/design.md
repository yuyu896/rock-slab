## Context

`audit_log` 装饰器（backend/apps/audit/decorators.py:44-53）在 update 前用 `view.get_object().__dict__` 全量序列化 `before_data`；User 继承 `AbstractBaseUser`，`__dict__` 含 `password` 哈希列。`after_data` 取自序列化器响应，UserSerializer 的 password 为 write_only，本就不出现（其余资源无凭据字段），但仍统一走脱敏管道以防未来序列化器变化。`AuditLog.before_data/after_data` 为 JSONField，生产已积累含哈希的历史行。

## Goals / Non-Goals

**Goals:**

- 写入端：任何审计记录不得再出现明文/哈希形式的敏感凭据字段
- 存量端：部署时自动清洗历史记录中的敏感值，无需人工脚本
- 审计证据不受损：脱敏保留键名（`password: '***'`），「修改过密码字段」这一事实仍可审计
- 逻辑单一事实：装饰器与迁移共用同一纯函数

**Non-Goals:**

- 不改审计的权限/可见性模型（view_audit 范围属另一议题）
- 不修 `is_success` 对 400 误记成功的缺陷（另案）
- 不对 `user_phone` / `ip_address` 等做脱敏（业务上审计本就要记录操作人）

## Decisions

**1. 脱敏 = 递归替换敏感键的值，键集合收在 `SENSITIVE_KEYS = {'password'}`。**
递归遍历 dict/list（before_data/after_data 均为 JSON 结构），命中键即把值替换为 `'***'`；同时剔除 `_state`（Django 内部属性，纯噪音）。不做「按值探测哈希格式」——按键白名单更稳、无假阴性风险；未来新增敏感字段（如 token）只需扩集合。

**2. 脱敏函数放 `apps/audit/utils.py`（`mask_sensitive`），装饰器与 0002 迁移共用。**
迁移 import 该函数逐行清洗——避免两处实现漂移。函数签名 `mask_sensitive(data) -> data'`（原地修改后返回，行级数据量小无性能顾虑）。

**3. 存量清洗走数据迁移（`audit/0002_mask_sensitive_fields`），不用管理命令。**
部署链路（deploy.sh → migrate）自动执行，不依赖人工记得跑命令；幂等（已脱敏的 `'***'` 再跑不变）。纯 DML 无 DDL，不触碰 [[pg-migration-dml-ddl-atomic]] 的 pending trigger 陷阱；逐行 `save(update_fields=['before_data', 'after_data'])`，生产量级（万级以内）秒级完成。只处理两字段任一非空的行，减少空转。

**4. after_data 同管道脱敏，尽管当前序列化器输出无 password。**
写入端统一收口，未来任何视图返回结构变化不再依赖人肉把关；成本一行。

## Risks / Trade-offs

- [`'***'` 使审计记录失去「密码是否真的变更」的值级证据] → 键的存在已表达「字段在快照中」；密码变更本身有 change_password 专属 action 语义可依
- [迁移遍历全表在大表上有耗时] → 仅遍历两字段非空行（`exclude(Q(before_data=None) & Q(after_data=None))`），量级可控；deploy 顺序在 collectstatic 之前无阻塞
- [清洗不可逆（原哈希不可恢复）] → 哈希本就不该在审计里，无恢复需求

## Migration Plan

代码 + 迁移同批部署；`migrate` 时自动清洗存量。回滚：revert 代码即可（已清洗数据无需恢复）。上线后验证：`GET /api/audit/{id}/` 任一 User update 记录的 `beforeData.password == '***'`。
