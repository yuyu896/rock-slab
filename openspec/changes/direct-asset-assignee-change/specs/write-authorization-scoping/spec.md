# write-authorization-scoping 增量

## ADDED Requirements

### Requirement: 固定资产使用人交接授权

固定资产使用人和部门交接 MUST 要求 `manage_instances` 操作权限，并 MUST 校验目标实例所属分公司在用户数据范围内。交接接口 MUST 只接受单个实例 ID，不得通过通用档案更新或批量维护绕过交接校验。

#### Scenario: 缺少权限或超出数据范围

- **WHEN** 用户缺少 `manage_instances` 权限，或目标实例超出其分公司数据范围
- **THEN** 系统拒绝请求且不修改实例或交接历史
