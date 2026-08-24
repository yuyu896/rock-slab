# sidebar-navigation Specification（修改）

## MODIFIED Requirements

### Requirement: 库存菜单结构与命名

PC 端主导航「库存」分组 SHALL 按以下顺序提供子菜单项：资产台账（`/assets/summary`，主视图）、实例档案（`/fixed-assets`）。已退役的「资产明细」（`/assets/list`）MUST 从菜单移除，旧路径 MUST 重定向到台账页。

#### Scenario: 库存子菜单顺序

- **WHEN** 已登录用户展开「库存」分组
- **THEN** 子菜单自上而下依次为「资产台账」「实例档案」

#### Scenario: 旧资产明细路径重定向

- **WHEN** 用户直接访问 `/assets/list`
- **THEN** 系统重定向到 `/assets/summary`，不出现 404

## REMOVED Requirements

### Requirement: 资产列表统一更名为资产明细
**Reason**: 资产明细页随 Asset 表退役整体下线（P2 第三刀），命名约定失去对象。
**Migration**: `/assets/list` 与 `/assets/list/create` 重定向到 `/assets/summary`。
