## ADDED Requirements

### Requirement: 员工列表按职级排序

员工列表 MUST 按 role 职级从高到低排序（admin > director > manager > supervisor > leader > staff），同职级按姓名升序。集团根节点选中时，无区域归属的高级别账号（行政总监 / 行政经理 / 管理员）因职级高而显示在列表最上层。

#### Scenario: 集团根列表高职级在前

- **WHEN** 点击「启航集团」根节点
- **THEN** 员工列表按职级排序，admin / director / manager 等高职级在前，staff 在后；无区域的高级别账号排在最上层

#### Scenario: 各节点员工均按职级排序

- **WHEN** 选中任意组织节点查看员工列表
- **THEN** 列表按职级排序（排序规则不因节点不同而改变）

### Requirement: 区域节点显示编码

组织树的区域节点 MUST 显示区域编码（`code`），格式如「区域名称（编码）」。

#### Scenario: 区域节点显示 name + code

- **WHEN** 查看组织树
- **THEN** 区域节点显示名称与编码，如「华东区域（HD）」
