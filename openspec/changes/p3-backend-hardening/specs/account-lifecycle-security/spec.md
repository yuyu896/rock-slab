## ADDED Requirements

### Requirement: Django Admin 不暴露用户模型编辑

Django Admin 站点 MUST NOT 注册 User 模型（反注册）：用户的增删改唯一入口为 API（`/api/users/`，含岗位权线闸、数据范围校验、审计日志与停用 token 联动）。Admin 站点保留其余业务模型的排障用途。运维需直接修用户数据时经 `manage.py shell`（会话留痕）。

#### Scenario: Admin 站点无用户模型

- **WHEN** 超管登录 `/admin/` 查看模型列表
- **THEN** 列表中不出现 User/用户 模型，无任何用户编辑表单入口

#### Scenario: 用户变更仍走 API 全套闸门

- **WHEN** 任何用户变更（含停用、改密、改岗）发生
- **THEN** 经 API 路径执行，受权线/范围/审计/token 联动约束，不存在绕过路径
