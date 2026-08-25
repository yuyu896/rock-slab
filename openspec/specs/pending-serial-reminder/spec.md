# pending-serial-reminder Specification

## Purpose
TBD - created by archiving change asset-v2-p3-pending-serial-reminder. Update Purpose after archive.
## Requirements
### Requirement: 侧边栏待补录徽标

侧边栏"实例档案"导航项 SHALL 显示待补录序列号的实例数量徽标：计数来自实例列表接口（`pending_serial=1`，仅取 count），MUST 遵循数据范围隔离（各用户只看到自己授权范围内的待补录数）；计数为 0 时 MUST NOT 显示徽标；接口失败时静默按 0 处理（不阻塞导航）。徽标挂载时拉取一次，MUST NOT 轮询。用户点击该导航项 SHALL 直达实例档案页，页面既有的"仅看待补录"筛选与补录入口不变。

#### Scenario: 有待补录时显示计数

- **WHEN** 用户范围内存在 5 台序列号为空的实例
- **THEN** 侧边栏"实例档案"子项显示徽标 5，点击进入实例档案页

#### Scenario: 无待补录不显示

- **WHEN** 用户范围内全部实例序列号已补录（或无实例）
- **THEN** "实例档案"子项不显示徽标

#### Scenario: 数据范围隔离

- **WHEN** 分公司 A 行政与分公司 B 行政同时在线，仅 A 有 3 台待补录
- **THEN** A 的徽标为 3，B 的徽标不显示（各自只看授权范围内计数）

#### Scenario: 计数接口失败静默

- **WHEN** 实例列表接口请求失败
- **THEN** 徽标按 0 处理（不显示），导航功能不受影响

