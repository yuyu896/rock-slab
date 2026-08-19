## ADDED Requirements

### Requirement: Import button in header
固定资产表页面头部 SHALL 在导出按钮右侧显示"批量导入"按钮，仅具有资产管理权限的用户可见。

#### Scenario: Import button visible for authorized users
- **WHEN** 用户拥有资产管理权限（canManageAssets）
- **THEN** 页面头部显示"批量导入"按钮

### Requirement: Import dialog with two steps
批量导入弹窗 SHALL 包含两个步骤：1) 下载导入模板；2) 上传填好的 Excel 文件。与 RecoveryList.vue 的导入流程一致。

#### Scenario: Download template
- **WHEN** 用户点击"下载模板"按钮
- **THEN** 系统下载固定资产导入模板 Excel 文件

#### Scenario: Upload and import
- **WHEN** 用户选择 Excel 文件并上传
- **THEN** 系统调用导入接口，显示导入中状态（loading spinner），完成后显示导入结果（成功条数和失败错误信息）

#### Scenario: Import success
- **WHEN** 导入完成且无错误
- **THEN** 弹窗显示"成功导入 N 条"，列表自动刷新

#### Scenario: Import with errors
- **WHEN** 导入完成但有部分失败
- **THEN** 弹窗显示成功条数和失败错误列表，用户可查看具体错误原因

#### Scenario: Import file type validation
- **WHEN** 用户选择的文件不是 .xlsx 或 .xls 格式
- **THEN** 文件选择器仅接受 .xlsx/.xls 格式，非 Excel 文件无法选择
