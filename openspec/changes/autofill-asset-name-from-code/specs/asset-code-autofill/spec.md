## ADDED Requirements

### Requirement: 按资产编号精确查询分类接口
系统 SHALL 提供 `GET /api/categories/lookup?asset_code=<code>`，按资产编号**精确**查询单条资产分类，供前端反查使用。

#### Scenario: 命中已登记编号
- **WHEN** 以已登记的 `asset_code` 查询
- **THEN** 返回 200 及该分类的 `asset_name`、`asset_category`、`item_category`、`unit`

#### Scenario: 未登记编号
- **WHEN** 以未登记的 `asset_code` 查询
- **THEN** 返回 404

#### Scenario: 缺少 asset_code 参数
- **WHEN** 未提供 `asset_code` 参数
- **THEN** 返回 400

### Requirement: 新增表单按编号自动带出资产名称
在含「资产编号」与「资产名称」手填字段的新增表单中，资产编号**失焦**时系统 SHALL 自动按编号查询分类并回填资产名称。

#### Scenario: 命中编号自动带出名称
- **WHEN** 用户在资产编号输入框输入已登记编号后离开该输入框（失焦）
- **THEN** 资产名称字段被自动填入分类登记的名称

#### Scenario: 同时带出类目与分类
- **WHEN** 表单含资产类目/物品分类字段且编号命中
- **THEN** 这些字段也被自动填入分类登记的对应值

### Requirement: 未登记编号的内联提示
资产编号失焦查询未命中时，表单 SHALL 在编号输入处**内联提示**「该编号未在资产分类登记」，不得静默无反馈。

#### Scenario: 输入未登记编号
- **WHEN** 用户输入未登记编号后失焦
- **THEN** 编号输入处显示「该编号未在资产分类登记」提示

### Requirement: 带出字段仍可编辑
自动带出的资产名称/类目/分类 SHALL 保持可编辑，系统不得锁定这些字段。

#### Scenario: 用户覆盖带出值
- **WHEN** 名称被自动带出后用户手动修改
- **THEN** 修改被接受，字段不被禁用或锁定

### Requirement: 多表单复用统一查询逻辑
各新增表单 SHALL 通过统一的查询/带出逻辑实现（如同一组合式），避免各自重复实现导致行为不一致。

#### Scenario: 多个表单一致行为
- **WHEN** 资产新增、领用、采购、退回、调拨等不同表单中输入同一编号并失焦
- **THEN** 它们带出与提示行为一致（均由同一逻辑驱动）
