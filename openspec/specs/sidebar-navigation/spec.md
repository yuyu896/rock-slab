# sidebar-navigation Specification

## Purpose
TBD - created by archiving change inventory-menu-rework. Update Purpose after archive.
## Requirements
### Requirement: 库存菜单结构与命名

PC 端主导航「库存」分组 SHALL 按以下顺序提供子菜单项：资产台账（`/assets/summary`，主视图）、实例档案（`/fixed-assets`）。已退役的「资产明细」（`/assets/list`）MUST 从菜单移除，旧路径 MUST 重定向到台账页。

#### Scenario: 库存子菜单顺序

- **WHEN** 已登录用户展开「库存」分组
- **THEN** 子菜单自上而下依次为「资产台账」「实例档案」

#### Scenario: 旧资产明细路径重定向

- **WHEN** 用户直接访问 `/assets/list`
- **THEN** 系统重定向到 `/assets/summary`，不出现 404

### Requirement: 子菜单可同时展开
侧边栏分组子菜单 SHALL 支持多个分组同时展开；展开一个分组 MUST NOT 自动收起其他已展开的分组，仅再次点击已展开的分组时收起该分组自身。

#### Scenario: 展开互不影响
- **WHEN** 用户已展开「库存」分组，再点击「资产流转」分组
- **THEN** 「资产流转」子菜单展开，且「库存」子菜单保持展开

#### Scenario: 收起自身
- **WHEN** 用户再次点击已展开的「库存」分组
- **THEN** 「库存」子菜单收起，其他已展开分组不受影响

