## REMOVED Requirements

### Requirement: Collapse all and expand all buttons

**Reason**: 功能与树节点自带的展开/收起图标重复，用户可逐个节点操作，批量操作使用场景少。

**Migration**: 用户点击树节点左侧的展开/收起图标来控制单个节点的展开状态。默认展开第一级节点，满足大部分浏览需求。

## ADDED Requirements

### Requirement: Simplified sidebar toolbar

组织架构侧边栏顶部工具栏 SHALL 仅保留必要的操作按钮，移除折叠/展开全部按钮。

#### Scenario: Sidebar toolbar only has add button
- **WHEN** 用户查看组织架构侧边栏
- **THEN** 工具栏仅显示"添加人员"按钮，不显示"折叠架构"和"展开架构"按钮

#### Scenario: Tree nodes remain expandable individually
- **WHEN** 用户点击树节点左侧的展开图标
- **THEN** 该节点展开显示子节点
