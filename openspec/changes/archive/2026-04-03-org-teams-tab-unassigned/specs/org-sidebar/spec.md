## MODIFIED Requirements

### Requirement: Unassigned personnel node in sidebar tree

侧边栏组织架构树 SHALL 在顶层末尾增加"未归属人员"虚拟节点，显示没有设置 `team` 和 `region` 归属的在职员工（排除 manager 角色）。

#### Scenario: Show unassigned personnel
- **WHEN** 存在满足条件的未归属员工（`status === 'active' && !team && !region && role !== 'manager'`）
- **THEN** 系统 SHALL 在树顶层末尾创建一个"未归属人员"节点，将这些员工作为其子节点

#### Scenario: No unassigned personnel
- **WHEN** 不存在满足条件的未归属员工
- **THEN** 系统 SHALL 不显示"未归属人员"节点

#### Scenario: Click unassigned person
- **WHEN** 用户点击"未归属人员"下的某个员工
- **THEN** 系统 SHALL 在详情面板中显示该员工的信息，与普通员工点击行为一致
