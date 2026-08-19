## ADDED Requirements

### Requirement: Supervisor and above can edit assets
admin、manager、supervisor 角色用户可通过 PUT/PATCH `/api/assets/{id}/` 编辑数据范围内的资产信息。编辑操作 MUST 受 DataScopeMixin 约束，只能修改自己区域/分公司内的资产。

#### Scenario: Supervisor edits asset in own region
- **WHEN** supervisor(P3) 用户 PATCH `/api/assets/{id}/` 且该资产的 branch 属于用户所在大区
- **THEN** 返回 200，资产信息更新成功

#### Scenario: Supervisor tries to edit asset outside own region
- **WHEN** supervisor(P3) 用户 PATCH `/api/assets/{id}/` 且该资产的 branch 不属于用户所在大区
- **THEN** 返回 404（因 DataScopeMixin 过滤后查询集为空）

#### Scenario: Leader tries to edit asset
- **WHEN** leader(P4) 用户 PATCH `/api/assets/{id}/`
- **THEN** 返回 403（权限不足）

### Requirement: Supervisor and above can delete assets
admin、manager、supervisor 角色用户可通过 DELETE `/api/assets/{id}/` 删除数据范围内的资产。删除为硬删除（从数据库移除记录）。

#### Scenario: Supervisor deletes asset in own region
- **WHEN** supervisor(P3) 用户 DELETE `/api/assets/{id}/` 且资产在自己的数据范围内
- **THEN** 返回 204，资产记录被删除

#### Scenario: Staff tries to delete asset
- **WHEN** staff(P5) 用户 DELETE `/api/assets/{id}/`
- **THEN** 返回 403

### Requirement: Branch fields auto-sync on edit
编辑资产时若 `branch` FK 被修改，系统 MUST 自动同步 CharField `分公司`（branch.name）和 `分公司编号`（branch.code），保持双字段一致。这两个 CharField 对客户端 MUST 为只读。

#### Scenario: Change branch FK updates denormalized fields
- **WHEN** 用户 PATCH 修改资产的 `branch` 为新分公司
- **THEN** `分公司` 自动更新为新分公司的 name，`分公司编号` 自动更新为新分公司的 code

#### Scenario: Client cannot directly set 分公司 CharField
- **WHEN** 用户 PATCH 请求中包含 `分公司` 或 `分公司编号` 字段
- **THEN** 这些字段值被忽略，由系统从 branch FK 自动填充

### Requirement: Leader and staff remain read-only
leader(P4) 和 staff(P5) 角色用户只能通过 GET 请求查看资产列表和详情，MUST NOT 有编辑/删除的 API 访问权限。前端 MUST NOT 显示编辑/删除操作入口。

#### Scenario: Leader can list assets in own branch
- **WHEN** leader(P4) 用户 GET `/api/assets/`
- **THEN** 返回 200，仅包含该用户所属分公司的资产

#### Scenario: Leader cannot access update endpoint
- **WHEN** leader(P4) 用户 PUT `/api/assets/{id}/`
- **THEN** 返回 403

### Requirement: Frontend edit UI for supervisor and above
资产列表页 MUST 为 supervisor 及以上角色显示编辑和删除操作按钮。编辑 MUST 打开预填当前资产信息的表单。删除 MUST 弹出二次确认对话框。

#### Scenario: Supervisor sees edit and delete buttons
- **WHEN** supervisor 角色用户打开资产列表页
- **THEN** 每行数据显示编辑和删除操作按钮

#### Scenario: Staff does not see edit and delete buttons
- **WHEN** staff 角色用户打开资产列表页
- **THEN** 每行数据不显示编辑和删除操作按钮

#### Scenario: Delete with confirmation
- **WHEN** 用户点击删除按钮
- **THEN** 弹出确认对话框，提示"确定删除该资产？此操作不可恢复"，确认后调用 DELETE API
