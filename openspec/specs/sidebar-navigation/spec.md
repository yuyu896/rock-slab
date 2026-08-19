# sidebar-navigation Specification

## Purpose
TBD - created by archiving change inventory-menu-rework. Update Purpose after archive.
## Requirements
### Requirement: 库存菜单结构与命名
PC 端主导航「库存」分组 SHALL 按以下顺序提供子菜单项：资产汇总（`/assets/summary`）、资产明细（`/assets/list`）、固定资产表（`/fixed-assets`）。

#### Scenario: 库存子菜单顺序
- **WHEN** 已登录用户展开「库存」分组
- **THEN** 子菜单自上而下依次为「资产汇总」「资产明细」「固定资产表」

### Requirement: 资产列表统一更名为资产明细
系统前端 SHALL 将原「资产列表」在菜单项、路由标题（`meta.title`）、页面标题及导出文件名前缀中统一显示为「资产明细」；路由路径 `/assets/list` 保持不变。

#### Scenario: 菜单与页面文案
- **WHEN** 用户查看「库存」子菜单或进入 `/assets/list` 页面
- **THEN** 菜单项与页面标题均显示「资产明细」

#### Scenario: 旧路径仍可访问
- **WHEN** 用户直接访问 `/assets/list`
- **THEN** 正常打开资产明细页面（路径未变更）

### Requirement: 子菜单可同时展开
侧边栏分组子菜单 SHALL 支持多个分组同时展开；展开一个分组 MUST NOT 自动收起其他已展开的分组，仅再次点击已展开的分组时收起该分组自身。

#### Scenario: 展开互不影响
- **WHEN** 用户已展开「库存」分组，再点击「资产流转」分组
- **THEN** 「资产流转」子菜单展开，且「库存」子菜单保持展开

#### Scenario: 收起自身
- **WHEN** 用户再次点击已展开的「库存」分组
- **THEN** 「库存」子菜单收起，其他已展开分组不受影响

