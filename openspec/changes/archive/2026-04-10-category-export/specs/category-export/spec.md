## ADDED Requirements

### Requirement: 分类数据 Excel 导出端点
CategoryViewSet SHALL 提供 `GET /api/categories/export/` 端点，将分类数据导出为 xlsx 文件。端点 SHALL 支持与列表接口相同的筛选参数（keyword、资产类目），仅导出筛选后的数据。

#### Scenario: 导出全部分类数据
- **WHEN** 用户发送 `GET /api/categories/export/` 请求（无筛选参数）
- **THEN** 系统返回包含所有分类记录的 xlsx 文件，文件名为 `分类数据导出.xlsx`

#### Scenario: 导出筛选后的分类数据
- **WHEN** 用户发送 `GET /api/categories/export/?keyword=电子` 请求
- **THEN** 系统仅返回匹配关键词的分类记录的 xlsx 文件

#### Scenario: 无数据时导出空文件
- **WHEN** 用户导出分类数据，但筛选结果为空
- **THEN** 系统返回仅含表头行的 xlsx 文件

### Requirement: 导出文件格式
导出的 xlsx 文件 SHALL 包含表头行和所有匹配数据的行。表头列顺序为：资产类目、物品分类、资产名称、资产编号、计量单位、资产数量、在库数量、警戒线、备注。

#### Scenario: 验证导出文件列结构
- **WHEN** 导出的 xlsx 文件被打开
- **THEN** 第 1 行为表头，列顺序依次为：资产类目、物品分类、资产名称、资产编号、计量单位、资产数量、在库数量、警戒线、备注

### Requirement: 前端导出按钮
Category.vue 页面头部 SHALL 提供"导出"按钮，点击后 SHALL 将当前筛选条件作为参数，触发后端导出端点下载 xlsx 文件。

#### Scenario: 点击导出按钮
- **WHEN** 用户在分类页面点击"导出"按钮
- **THEN** 浏览器下载一个 xlsx 文件，包含当前筛选条件下的分类数据

#### Scenario: 带筛选条件导出
- **WHEN** 用户已筛选资产类目为"固定资产类"，然后点击"导出"按钮
- **THEN** 下载的文件仅包含固定资产类目下的分类数据
