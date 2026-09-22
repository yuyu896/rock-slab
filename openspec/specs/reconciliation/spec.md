# reconciliation Specification

## Purpose
TBD - created by archiving change reconciliation-nav-placeholder. Update Purpose after archive.
## Requirements
### Requirement: 对账模块导航占位

系统 SHALL 在主导航提供「对账」模块入口（位于资产盘点与组织架构之间），占位期仅系统管理员可见；对应路由 `/reconciliation` SHALL 受 admin 守卫保护。占位页 SHALL 为空白页（仅页面标题），MUST NOT 包含任何业务功能、模拟数据或不可用操作；对账业务功能（账单导入、序列号比对、差异处理）由后续专门提案定义。

#### Scenario: 管理员看到对账入口

- **WHEN** 系统管理员登录后查看导航
- **THEN** 「资产盘点」与「组织架构」之间显示「对账」项，点击进入 `/reconciliation` 空白占位页

#### Scenario: 非管理员不可见且直达被拦

- **WHEN** 非管理员登录，或直接访问 `/reconciliation`
- **THEN** 导航不显示「对账」项，路由守卫将其重定向至工作台

