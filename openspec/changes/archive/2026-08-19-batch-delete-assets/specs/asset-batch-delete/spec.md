## ADDED Requirements

### Requirement: 资产列表批量删除
资产列表 SHALL 支持勾选多条资产后一次性删除；入口位于既有批量操作栏。

#### Scenario: 勾选并批量删除
- **WHEN** 用户在资产列表勾选多条并点击「批量删除」，在确认弹窗中确认
- **THEN** 所选资产被删除，列表刷新，已选清空

#### Scenario: 无选择时不可用
- **WHEN** 未勾选任何资产
- **THEN** 「批量删除」不可用（或点击时提示请先选择）

#### Scenario: 批量删除需 manage_assets 权限
- **WHEN** 当前用户无 `manage_assets` 授权
- **THEN** 看不到「批量删除」入口

### Requirement: 固定资产表批量删除
固定资产表 SHALL 支持勾选多条后一次性删除。

#### Scenario: 勾选并批量删除
- **WHEN** 用户在固定资产表勾选多条并点击「批量删除」，确认后执行
- **THEN** 所选固定资产被删除，列表刷新，已选清空

#### Scenario: 无选择时不可用
- **WHEN** 未勾选任何固定资产
- **THEN** 「批量删除」不可用（或点击时提示请先选择）

### Requirement: 后端批量删除接口
系统 SHALL 提供资产与固定资产的批量删除接口（`POST`，接收 `ids` 列表），按数据范围过滤后删除，并返回实际删除数量。

#### Scenario: 删除范围内的 ids
- **WHEN** 以有权管理的 ids 调用批量删除
- **THEN** 这些记录被删除，返回 `{ deleted: <实际删除数> }`

#### Scenario: 越权 id 被数据范围排除
- **WHEN** 提交的 ids 含当前用户数据范围之外的记录
- **THEN** 越权记录不被删除（不计入 deleted），不报错

### Requirement: 批量删除权限与单删一致
批量删除 SHALL 要求与单条删除相同的 `manage_assets` 权限；无权限者调用接口被拒（403）且看不到入口。

#### Scenario: 无权限调用被拒
- **WHEN** 无 `manage_assets` 的用户调用批量删除接口
- **THEN** 返回 403

### Requirement: 删除后刷新并清空选择
批量删除成功后 SHALL 刷新当前列表并清空已选集合。

#### Scenario: 删除成功后状态更新
- **WHEN** 批量删除成功
- **THEN** 列表重新加载、已选集合清空、显示成功提示
