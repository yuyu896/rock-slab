## ADDED Requirements

### Requirement: 资产模块提供专用模板下载接口
后端 `AssetViewSet` SHALL 提供一个 `download_template` action（`GET /api/assets/template`），返回仅含表头行（无数据行）的 xlsx 文件。表头列顺序 SHALL 为：序号、分公司、资产编号、分公司编号、资产类目、电脑序列号、供应商、物品分类、资产名称、图片、入库日期、是否租用、数量、规格、单价、购入金额、出库日期、所属部门、使用人、当前状态、警戒线、是否充足、备注（共 23 列）。

#### Scenario: 下载资产导入模板
- **WHEN** 调用 `GET /api/assets/template`
- **THEN** 返回 HTTP 200，Content-Type 为 xlsx，文件包含 1 行表头 + 0 行数据

#### Scenario: 模板列数和顺序正确
- **WHEN** 打开下载的模板文件
- **THEN** 表头 SHALL 有恰好 23 列，第 3 列为"资产编号"、第 6 列为"电脑序列号"、第 10 列为"图片"

### Requirement: 流转模块提供专用模板下载接口
后端 `TransferViewSet` SHALL 提供一个 `download_template` action（`GET /api/transfers/template`），返回仅含表头行的 xlsx 文件。表头列顺序 SHALL 与现有导出一致：调拨日期、流转类型、调出分公司、调出部门、调入分公司、调入部门、资产编号、资产名称、规格型号、调拨数量、调拨原因、调出负责人、调入负责人、备注（共 14 列）。

#### Scenario: 下载流转导入模板
- **WHEN** 调用 `GET /api/transfers/template`
- **THEN** 返回 HTTP 200，Content-Type 为 xlsx，文件包含 1 行表头 + 0 行数据

#### Scenario: 无数据时模板不为空白
- **WHEN** 数据库中无任何流转记录
- **AND** 调用 `GET /api/transfers/template`
- **THEN** 模板文件 SHALL 仍包含完整的表头行

### Requirement: 资产导入/导出列顺序统一为新的 23 列排列
后端 `AssetViewSet` 的 `import_excel` 和 `export_excel` action SHALL 使用新的列顺序：序号、分公司、资产编号、分公司编号、资产类目、电脑序列号、供应商、物品分类、资产名称、图片、入库日期、是否租用、数量、规格、单价、购入金额、出库日期、所属部门、使用人、当前状态、警戒线、是否充足、备注。导入时"图片"列 SHALL 被跳过不处理。导出时"图片"列 SHALL 输出图片 URL 字符串。

#### Scenario: 导出文件使用新列顺序
- **WHEN** 调用 `GET /api/assets/export`
- **THEN** Excel 表头第 3 列 SHALL 为"资产编号"、第 6 列 SHALL 为"电脑序列号"、第 10 列 SHALL 为"图片"

#### Scenario: 导入按新列顺序解析
- **WHEN** 上传一个按新 23 列顺序填写的 Excel 文件
- **THEN** 系统 SHALL 正确解析每列数据，分公司编号从第 4 列读取、电脑序列号从第 6 列读取

#### Scenario: 图片列导入跳过
- **WHEN** 导入的 Excel 第 10 列（图片）包含内容
- **THEN** 系统 SHALL 跳过该列不报错，其余列正常导入

### Requirement: 所有导入弹窗使用专用模板 API 下载模板
所有前端导入弹窗（AssetImportDialog、PurchaseImportDialog、CategoryImportDialog、流转页面内联弹窗）SHALL 通过专用模板 API 下载空模板文件，SHALL NOT 依赖全量数据导出或静态文件。

#### Scenario: AssetImportDialog 下载空模板
- **WHEN** 用户在资产列表点击"下载模板"
- **THEN** 前端 SHALL 调用 `GET /api/assets/template` 获取仅含表头的 xlsx 文件

#### Scenario: PurchaseImportDialog 下载空模板
- **WHEN** 用户在采购页面点击"下载模板"
- **THEN** 前端 SHALL 调用 `GET /api/assets/template` 获取仅含表头的 xlsx 文件

#### Scenario: 流转页面下载空模板
- **WHEN** 用户在流转页面（PurchaseList/TransferList/AssignList）点击"下载模板"
- **THEN** 前端 SHALL 调用 `GET /api/transfers/template` 获取仅含表头的 xlsx 文件

### Requirement: 所有导入弹窗样式统一
所有导入弹窗 SHALL 具有一致的视觉样式：弹窗标题格式为"批量导入[模块名]"、包含下载模板按钮（次要样式）、上传区域（虚线边框 + 图标 + 提示文字）、确认导入按钮（主要样式）、导入结果展示（成功 N 条 / 失败 N 条）。

#### Scenario: 弹窗标题格式一致
- **WHEN** 打开任意模块的导入弹窗
- **THEN** 弹窗标题 SHALL 为"批量导入"后跟模块名称

#### Scenario: 上传区域样式一致
- **WHEN** 比较任意两个导入弹窗的上传区域
- **THEN** 两者 SHALL 使用相同的边框样式、图标和提示文字布局
