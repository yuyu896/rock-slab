## ADDED Requirements

### Requirement: Excel 分类模板下载
CategoryViewSet SHALL 提供 `GET /api/categories/template/` 端点，返回分类导入 Excel 模板文件（.xlsx 格式）。模板包含表头行：资产类目、物品分类、资产名称、资产编号、计量单位、警戒线、备注。

#### Scenario: 下载分类导入模板
- **WHEN** 前端发送 `GET /api/categories/template/` 请求
- **THEN** 后端 SHALL 返回 Content-Type 为 `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` 的 xlsx 文件，包含上述表头行

### Requirement: Excel 批量导入分类
CategoryViewSet SHALL 提供 `POST /api/categories/import/` 端点，接收 multipart/form-data 格式的 Excel 文件，解析后批量创建 Category 记录。响应 SHALL 包含 `imported`（成功数）和 `errors`（失败详情数组）。

#### Scenario: 成功导入分类数据
- **WHEN** 前端上传格式正确的 Excel 文件，包含 5 行有效数据
- **THEN** 后端 SHALL 创建 5 条 Category 记录，返回 `{imported: 5, errors: []}`

#### Scenario: 部分行导入失败
- **WHEN** 上传的 Excel 中有 3 行有效数据和 2 行无效数据（如缺少必填字段）
- **THEN** 后端 SHALL 创建 3 条记录，返回 `{imported: 3, errors: ["第 X 行: ...", "第 Y 行: ..."]}`

#### Scenario: 未上传文件
- **WHEN** 前端发送 POST 请求但未附带 file 字段
- **THEN** 后端 SHALL 返回 400 错误，提示"请上传文件"

#### Scenario: 文件格式无法解析
- **WHEN** 前端上传非 Excel 格式文件
- **THEN** 后端 SHALL 返回 400 错误，提示文件解析失败
