# asset-create-validation Specification

## Purpose
TBD - created by archiving change fix-asset-create-400. Update Purpose after archive.
## Requirements
### Requirement: 固定资产按资产编号创建
通过 `POST /api/assets/fixed-assets` 创建固定资产实例时，`asset`（关联品目外键）不得为请求必填项；当请求仅提供 `资产编号` 时，系统 SHALL 在品目表中按 `资产编号` 反查父级 `Asset` 并自动关联。反查成功后，实例的 `资产名称`、`分公司`、`分公司编号`、`branch` SHALL 从父级品目继承（若请求未另行提供）。

#### Scenario: 仅传资产编号创建固定资产成功
- **WHEN** 客户端 `POST /api/assets/fixed-assets`，提交合法 `资产编号`（该编号已存在于品目表）及实例字段（序列号、供应商、入库日期、当前状态等），但不提交 `asset` 外键
- **THEN** 系统返回 **201 Created**，且响应中 `asset` 等于对应品目的主键，`资产名称`、`分公司`、`分公司编号` 已从品目继承

#### Scenario: 资产编号不存在时拒绝创建
- **WHEN** 客户端提交的 `资产编号` 在品目表中不存在，且未提交 `asset` 外键
- **THEN** 系统返回 **400 Bad Request**，错误信息明确指出资产编号不存在

#### Scenario: 直接提交品目外键仍可创建
- **WHEN** 客户端直接提交合法的 `asset`（品目主键）
- **THEN** 系统使用该外键关联品目并返回 **201 Created**

### Requirement: 资产创建时序号由后端自增
通过 `POST /api/assets/` 创建资产（品目）时，`序号` 不得为请求必填项。当请求未提供 `序号` 时，系统 SHALL 取当前品目表最大 `序号` 加 1 作为新值。

#### Scenario: 不传序号创建资产成功
- **WHEN** 客户端 `POST /api/assets/`，提交必填业务字段（资产编号、资产名称、资产类目、物品分类、数量等）但不提交 `序号`
- **THEN** 系统返回 **201 Created**，且新记录的 `序号` 等于「当前最大序号 + 1」

#### Scenario: 显式传序号时予以保留
- **WHEN** 客户端显式提交 `序号`
- **THEN** 系统使用客户端提交的 `序号` 值创建记录

### Requirement: 资产创建时按分公司名称关联分公司
通过 `POST /api/assets/` 创建资产时，系统 SHALL 接受以分公司**名称**提交的 `分公司` 字段。当提交了 `分公司` 名称但未提交 `branch` 外键时，系统 SHALL 按名称查询 `Branch`，并回填 `branch` 外键与 `分公司编号`，使新建资产行归属于正确分公司，保证数据隔离生效。

#### Scenario: 提交分公司名称创建资产并回填关联
- **WHEN** 客户端提交 `分公司`（分公司名称，该名称存在于分公司表），但未提交 `branch` 与 `分公司编号`
- **THEN** 系统返回 **201 Created**，新记录的 `branch` 等于对应分公司主键，`分公司编号` 等于该分公司 `code`

#### Scenario: 分公司名称无法解析时不阻断创建
- **WHEN** 客户端提交的 `分公司` 名称在分公司表中不存在
- **THEN** 系统仍创建资产（`branch` 置空），返回 **201 Created**，不因分公司解析失败而返回错误

### Requirement: 资产编号须在资产分类登记
通过 `POST /api/assets/` 创建或更新资产时，提交的 `资产编号` SHALL 已存在于资产分类（Category）的 `asset_code` 字典中。未登记时系统 SHALL 返回 **400 Bad Request** 并提示「该资产编号未在资产分类登记」，不创建/不修改记录。仅当请求未携带 `资产编号`（如部分更新的 PATCH）时跳过该校验。

#### Scenario: 未登记的资产编号被拒绝
- **WHEN** 客户端 `POST /api/assets/`，提交的 `资产编号` 不存在于资产分类表
- **THEN** 系统返回 **400 Bad Request**，错误体含 `资产编号` 字段及「资产分类」字样，且不创建记录

#### Scenario: 已登记的资产编号创建成功
- **WHEN** 客户端提交的 `资产编号` 已存在于资产分类表
- **THEN** 系统正常创建资产，返回 **201 Created**

