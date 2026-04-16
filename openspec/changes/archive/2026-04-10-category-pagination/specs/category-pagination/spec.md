## ADDED Requirements

### Requirement: 后端分类列表分页
CategoryViewSet 的列表接口 SHALL 支持分页。响应格式 SHALL 为 `{count: number, next: string|null, previous: string|null, results: Category[]}`。默认每页 20 条，支持 `page` 和 `pageSize` 查询参数。

#### Scenario: 获取第一页数据
- **WHEN** 前端发送 `GET /api/categories/?page=1&pageSize=20`
- **THEN** 后端返回 `{count: <总数>, next: <下一页URL>, previous: null, results: [<前20条数据>]}`

#### Scenario: 获取第二页数据
- **WHEN** 前端发送 `GET /api/categories/?page=2&pageSize=20`
- **THEN** 后端返回 `{count: <总数>, next: <下一页URL或null>, previous: <上一页URL>, results: [<第21-40条数据>]}`

#### Scenario: 带筛选条件的分页
- **WHEN** 前端发送 `GET /api/categories/?page=1&资产类目=固定资产类`
- **THEN** 后端返回筛选后的分页数据

### Requirement: 前端分页组件
Category.vue 页面 SHALL 在表格视图和卡片视图下方展示分页组件，包含页码按钮、上一页/下一页按钮、每页条数选择器。

#### Scenario: 点击页码切换
- **WHEN** 用户点击分页组件中的页码按钮"2"
- **THEN** 表格/卡片展示第 2 页数据，分页组件更新当前页高亮

#### Scenario: 切换每页条数
- **WHEN** 用户在每页条数选择器中选择"50条/页"
- **THEN** 页面重新加载，每页展示 50 条数据，重置到第 1 页

### Requirement: 筛选条件变更时重置分页
当筛选条件（资产类目、关键词）变更时，分页 SHALL 自动重置到第 1 页。

#### Scenario: 切换筛选后重置页码
- **WHEN** 用户在第 3 页时切换了资产类目筛选条件
- **THEN** 页面自动跳转回第 1 页，展示筛选后的第一页数据
