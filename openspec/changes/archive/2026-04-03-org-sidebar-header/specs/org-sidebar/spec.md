## MODIFIED Requirements

### Requirement: Sidebar toolbar has title and add button

侧边栏工具栏 SHALL 在左侧显示当前组织名称"启航事业部"作为标题，右侧显示"新增人员"按钮。

#### Scenario: Toolbar shows organization title
- **WHEN** 用户查看组织架构侧边栏
- **THEN** 工具栏左侧显示"启航事业部"标题文字

#### Scenario: Tree starts from region nodes
- **WHEN** 用户查看组织架构树
- **THEN** 树直接显示区域节点、行政经理节点，不再有"集团"根节点

## REMOVED Requirements

### Requirement: Tree has root node

**Reason**: 根节点"集团"移到工具栏作为标题，不再作为树节点。

**Migration**: 行政经理和区域节点直接作为顶层节点显示。
