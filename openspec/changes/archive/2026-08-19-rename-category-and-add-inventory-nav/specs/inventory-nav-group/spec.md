## ADDED Requirements

### Requirement: 资产分类 renamed to 品目
侧边栏导航中「资产分类」MUST 显示为「品目」。Category.vue 页面标题 MUST 同步改为「品目」。路由 path `/categories` 不变。

#### Scenario: Sidebar shows 品目
- **WHEN** 用户查看 PC 端侧边栏
- **THEN** 原来的「资产分类」菜单项显示为「品目」

#### Scenario: Category page title
- **WHEN** 用户点击「品目」进入分类管理页面
- **THEN** 页面标题显示为「品目」

### Requirement: 库存 navigation group
侧边栏 MUST 新增「库存」一级分组（可展开/折叠），包含「资产列表」和「固定资产表」两个子项。「资产列表」MUST 从顶层菜单移入此分组下。

#### Scenario: 库存 group structure
- **WHEN** 用户查看 PC 端侧边栏
- **THEN** 可见「库存」分组，展开后显示「资产列表」和「固定资产表」两个子菜单项

#### Scenario: 资产列表 moved under 库存
- **WHEN** 用户点击库存分组下的「资产列表」
- **THEN** 导航到 `/assets/list`，资产列表页面正常加载

### Requirement: 固定资产表 page
MUST 新增固定资产表页面（路由 `/fixed-assets`），展示资产类目为「固定」的资产列表。MUST 复用 getAssets API 并默认传入 `category=固定` 筛选。

#### Scenario: Fixed asset list loads filtered data
- **WHEN** 用户点击库存分组下的「固定资产表」
- **THEN** 导航到 `/fixed-assets`，页面加载并仅展示资产类目为「固定」的资产数据

#### Scenario: Fixed asset list supports filtering
- **WHEN** 用户在固定资产表中使用分公司、状态、关键词筛选
- **THEN** 筛选在「固定」资产类目范围内生效
