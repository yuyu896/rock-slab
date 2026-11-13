## ADDED Requirements

### Requirement: ItemPicker 支持按管理方式筛选

品目选择组件（ItemPicker）MUST 支持接受可选 prop `managementType`，当传入时：
- 全量字典模式（`stockColumn` 未传）：将 `管理方式` 参数透传给 `getCategories` API，由后端过滤
- 台账模式（`stockColumn` 已传）：在前端对返回结果按 `managementType` 过滤

组件 MUST NOT 自行渲染管理方式筛选 UI，筛选值由父组件通过 prop 控制。

#### Scenario: 全量字典模式按管理方式过滤

- **WHEN** ItemPicker 接收 `managementType="instance"` 且未传 `stockColumn`
- **THEN** 远程搜索请求携带 `管理方式=instance` 参数，仅返回实例管理品目

#### Scenario: 台账模式按管理方式前端过滤

- **WHEN** ItemPicker 接收 `managementType="quantity"` 且传入 `stockColumn`
- **THEN** `getAssetStocks` 返回结果中 `managementType !== 'quantity'` 的选项被过滤掉

#### Scenario: 未传 managementType 不过滤

- **WHEN** ItemPicker 未接收 `managementType` prop
- **THEN** 返回全部管理方式的品目，行为与改动前一致

### Requirement: ItemPicker 搜索框提示用户名称/编号搜索

品目选择组件的搜索框 placeholder MUST 提示用户可按编号或名称搜索（默认文字为「支持按编号或名称搜索」）。调用方传入 `placeholder` prop 时 MUST 覆盖默认文字。

#### Scenario: 默认 placeholder 显示搜索提示

- **WHEN** 渲染 ItemPicker 且未传 `placeholder` prop 且组件不处于禁用状态
- **THEN** 搜索框显示「支持按编号或名称搜索」

#### Scenario: 传入 placeholder prop 时覆盖默认值

- **WHEN** 渲染 ItemPicker 且传入 `placeholder="请选择品目"`
- **THEN** 搜索框显示「请选择品目」
