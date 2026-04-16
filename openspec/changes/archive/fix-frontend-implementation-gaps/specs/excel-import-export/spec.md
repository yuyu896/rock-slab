## ADDED Requirements

### Requirement: 分类 Excel 模板下载
Category.vue SHALL 提供"下载模板"功能，下载分类导入的 Excel 模板文件（含表头示例）。

#### Scenario: 下载分类导入模板
- **WHEN** 用户点击分类页面的"下载模板"按钮
- **THEN** 系统下载预定义的分类导入 Excel 模板文件

### Requirement: 分类 Excel 导入
Category.vue SHALL 提供文件上传功能，支持上传填写好的分类 Excel 文件，调用 `POST /api/categories/import` 接口批量导入分类数据。导入完成后显示成功数量和失败原因。

#### Scenario: 成功导入分类数据
- **WHEN** 用户上传格式正确的分类 Excel 文件
- **THEN** 系统调用导入 API，显示"成功导入 X 条分类数据"

#### Scenario: 导入部分失败
- **WHEN** 上传的 Excel 中部分行数据有误
- **THEN** 系统显示"成功导入 X 条，失败 Y 条"，并列出失败原因

### Requirement: 采购 Excel 模板下载
Purchase.vue SHALL 提供"下载模板"功能，下载采购入库单的 Excel 模板文件。

#### Scenario: 下载采购导入模板
- **WHEN** 用户点击采购页面的"下载模板"按钮
- **THEN** 系统下载预定义的采购导入 Excel 模板文件

### Requirement: 采购 Excel 导入确认
Purchase.vue 导入模态框中的"确认导入"按钮 SHALL 触发文件上传，调用 `importAssets` API，并展示导入结果。

#### Scenario: 确认导入采购数据
- **WHEN** 用户选择文件后点击"确认导入"
- **THEN** 系统调用 `POST /api/assets/import` 上传文件，显示导入结果（成功数和错误列表）

### Requirement: 流转导出功能
Transfer.vue SHALL 提供导出按钮，将当前筛选条件下的流转记录导出为 Excel 文件。

#### Scenario: 导出流转记录
- **WHEN** 用户点击流转页面的"导出"按钮
- **THEN** 系统将当前筛选条件下的流转记录导出为 Excel 文件并下载

### Requirement: 报表导出功能
Reports.vue SHALL 提供导出按钮，将当前报表数据导出为 Excel 文件。

#### Scenario: 导出报表
- **WHEN** 用户点击报表页面的"导出"按钮
- **THEN** 系统将当前展示的报表数据导出为 Excel 文件并下载
