## ADDED Requirements

### Requirement: 导入接口校验上传文件

所有 Excel 导入接口（assets / categories / transfers / inventories 的 `import_excel`）SHALL 对上传文件执行统一校验：扩展名 MUST 为 `.xlsx`、Content-Type MUST 匹配 OpenXML 电子表格、文件大小 MUST 不超过配置的上限、解析后的数据行数 MUST 不超过配置的行数上限。任一校验失败 SHALL 返回 400 并给出明确错误，且 MUST NOT 开始数据库写入或继续解压解析。

#### Scenario: 上传非 xlsx 文件

- **WHEN** 用户上传一个 `.exe` 或 `.csv` 文件到导入接口
- **THEN** 系统返回 400 提示文件类型不被允许，且不调用 `load_workbook`

#### Scenario: 上传超大文件

- **WHEN** 用户上传一个超过配置大小上限的文件
- **THEN** 系统返回 400 提示文件过大，MUST NOT 将其完整读入内存解压

#### Scenario: 上传超出行数上限的表

- **WHEN** 用户上传一个合法但数据行数超过上限（如 50000 行）的 xlsx
- **THEN** 系统返回 400 提示行数超限，MUST NOT 继续逐行处理

### Requirement: 导入模板必须可成功导出

"下载导入模板"接口 SHALL 能成功生成并返回有效的 `.xlsx` 文件，MUST NOT 因样式对象使用非法枚举值（如 `openpyxl` `Alignment(vertical='middle')`）而抛出 500。所有 `Alignment` 的 `vertical` 参数 SHALL 使用合法值集合 `{top, center, bottom, justify, distributed}` 之一。

#### Scenario: 下载固定资产导入模板

- **WHEN** 已授权用户请求下载固定资产导入模板
- **THEN** 系统返回 200 与一个可被 `openpyxl.load_workbook` 正常打开的 `.xlsx` 文件

### Requirement: 上传体积限制与部署配置一致

Nginx 的 `client_max_body_size` 与 Django 的 `DATA_UPLOAD_MAX_MEMORY_SIZE` / `FILE_UPLOAD_MAX_MEMORY_SIZE` SHALL 配置为不小于实际最大导入模板体积的值，确保合法导入不会被网关以 413 拦截。

#### Scenario: 上传接近模板体积的合法文件

- **WHEN** 用户上传一个与"资产导入模板"体积相当（数十 MB）的合法 xlsx
- **THEN** 请求到达应用层进行校验，MUST NOT 被 Nginx 以 413 Request Entity Too Large 拒绝
