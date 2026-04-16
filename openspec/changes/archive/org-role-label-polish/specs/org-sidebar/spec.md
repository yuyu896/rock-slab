## MODIFIED Requirements

### Requirement: Sidebar toolbar has title and add button

侧边栏工具栏 SHALL 在左侧显示当前组织名称"启航事业部"作为标题，右侧显示"新增人员"按钮。
树节点和人员详情中的角色标签 SHALL 仅显示角色文字名称（如"行政经理"、"行政主管"），不显示 emoji 图标。
角色标签 SHALL 使用深色文字搭配浅色背景，确保在各显示场景中文字清晰可读。

#### Scenario: Toolbar shows organization title
- **WHEN** 用户查看组织架构侧边栏
- **THEN** 工具栏左侧显示"启航事业部"标题文字

#### Scenario: Tree starts from region nodes
- **WHEN** 用户查看组织架构树
- **THEN** 树直接显示区域节点、行政经理节点，不再有"集团"根节点

#### Scenario: Tree nodes remain expandable individually
- **WHEN** 用户点击树节点左侧的展开图标
- **THEN** 该节点展开显示子节点

#### Scenario: Role label displays text only without emoji
- **WHEN** 用户在侧边栏树或人员详情中查看角色标签
- **THEN** 标签仅显示角色文字名称（如"行政经理"），不包含 emoji 图标

#### Scenario: Role label text has sufficient contrast
- **WHEN** 用户查看任意角色的角色标签
- **THEN** 文字颜色为深色（oklch 明度 ≤ 0.40 或 CSS 变量引用的深色值），背景为浅色
