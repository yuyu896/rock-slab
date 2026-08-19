## ADDED Requirements

### Requirement: 后端批量导入 API
TransferViewSet SHALL 提供 `import_excel` action（POST `/api/transfers/import`），接受 Excel 文件上传，逐行解析并创建 Transfer 记录。每行 SHALL 包含 action_type 字段（中文标签），后端 SHALL 自动映射为对应的 action_type 值。导入结果 SHALL 返回 `{ imported: number, errors: string[] }`。

#### Scenario: 批量导入成功
- **WHEN** 用户上传包含多条流转记录的 Excel 文件
- **THEN** 系统创建对应数量的 Transfer 记录（默认审批状态为"待审批"），返回成功数量

#### Scenario: 部分行 action_type 无效
- **WHEN** Excel 中某行的 action_type 不在可识别的中文标签列表中
- **THEN** 该行记录导入失败，errors 中包含行号和错误原因，其他有效行正常导入

### Requirement: 后端导出/模板下载 API
TransferViewSet SHALL 提供 `export_excel` action（GET `/api/transfers/export`），导出流转记录 Excel。无数据时 SHALL 仅输出表头行作为导入模板。

#### Scenario: 下载导入模板
- **WHEN** 用户调用 export 接口且无筛选条件
- **THEN** 系统返回包含表头行的 Excel 文件

### Requirement: 前端批量导入按钮
资产流转页面操作栏 SHALL 在"导出"和"新建流转"按钮旁显示"批量导入"按钮。

#### Scenario: 点击批量导入按钮
- **WHEN** 用户在资产流转页面点击"批量导入"按钮
- **THEN** 系统打开批量导入弹窗

### Requirement: 前端批量导入弹窗
批量导入弹窗 SHALL 支持下载模板、上传 Excel 文件、展示导入结果。交互流程与资产列表批量导入一致。

#### Scenario: 下载模板
- **WHEN** 用户在弹窗中点击"下载模板"
- **THEN** 系统下载包含流转记录字段的 Excel 模板

#### Scenario: 上传成功
- **WHEN** 用户上传有效 Excel 文件
- **THEN** 系统显示导入结果，全部成功时自动关闭弹窗并刷新列表

#### Scenario: 文件格式校验
- **WHEN** 用户上传非 Excel 文件
- **THEN** 系统提示"请上传 Excel 文件（.xlsx 或 .xls）"
