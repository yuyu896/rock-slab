## ADDED Requirements

### Requirement: Category attribute_template 字段持久化
Category 模型 SHALL 包含 `attribute_template` 字段（JSONField），用于存储该分类的动态属性模板配置。字段默认值为空对象 `{}`，可为空。

#### Scenario: 创建分类时保存属性模板
- **WHEN** 前端发送 `POST /api/categories/` 请求，body 中包含 `attribute_template: [{name: "CPU型号", type: "text", required: true, options: ""}]`
- **THEN** 后端 SHALL 将该 JSON 数据存储到 Category 的 `attribute_template` 字段中，并在 GET 响应中原样返回

#### Scenario: 更新分类的属性模板
- **WHEN** 前端发送 `PUT /api/categories/:id/` 请求，body 中包含更新后的 `attribute_template` 数组
- **THEN** 后端 SHALL 更新该分类的 `attribute_template` 字段

#### Scenario: 不传 attribute_template 时使用默认值
- **WHEN** 创建分类时未传入 `attribute_template` 字段
- **THEN** 后端 SHALL 存储默认空对象 `{}`

### Requirement: attribute_template 数据格式校验
CategorySerializer SHALL 校验 `attribute_template` 字段的基本结构：如果提供，MUST 为数组/对象格式。数组中每个元素如果存在，SHALL 包含 `name` 和 `type` 字段。

#### Scenario: 提交非法格式的 attribute_template
- **WHEN** 前端提交 `attribute_template: "invalid"`（非数组/对象）
- **THEN** 后端 SHALL 返回 400 错误，提示格式不正确

#### Scenario: 提交空数组
- **WHEN** 前端提交 `attribute_template: []`
- **THEN** 后端 SHALL 正常保存空数组
