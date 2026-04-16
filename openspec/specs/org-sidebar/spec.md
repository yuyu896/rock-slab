### Requirement: Sidebar toolbar has title and add button

侧边栏工具栏 SHALL 在左侧显示当前组织名称"启航事业部"作为标题，右侧显示"新增人员"按钮。

#### Scenario: Toolbar shows organization title
- **WHEN** 用户查看组织架构侧边栏
- **THEN** 工具栏左侧显示"启航事业部"标题文字

#### Scenario: Tree starts from region nodes
- **WHEN** 用户查看组织架构树
- **THEN** 树直接显示区域节点、行政经理节点，不再有"集团"根节点

#### Scenario: Tree nodes remain expandable individually
- **WHEN** 用户点击树节点左侧的展开图标
- **THEN** 该节点展开显示子节点

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
