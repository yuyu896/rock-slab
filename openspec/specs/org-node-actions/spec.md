### Requirement: Node detail panel has edit and delete buttons

组织架构节点详情面板 SHALL 显示"编辑"和"删除"两个操作按钮，用于修改或删除当前选中的节点。

#### Scenario: Person node shows edit and delete buttons
- **WHEN** 用户在组织架构树中选中一个人员节点
- **THEN** 右侧详情面板顶部显示"编辑"和"删除"按钮

#### Scenario: Edit button opens modal
- **WHEN** 用户点击"编辑"按钮
- **THEN** 系统打开编辑弹窗，表单预填当前节点的数据

#### Scenario: Delete button confirms before deletion
- **WHEN** 用户点击"删除"按钮
- **THEN** 系统显示确认对话框，确认后执行删除操作

### Requirement: Region and team nodes also have action buttons

区域节点和行政组节点的详情面板 SHALL 同样显示"编辑"和"删除"按钮。

#### Scenario: Region node shows edit button
- **WHEN** 用户选中一个区域节点
- **THEN** 详情面板显示"编辑"按钮（删除按钮可选，视业务规则而定）

#### Scenario: Team node shows edit and delete buttons
- **WHEN** 用户选中一个行政组节点
- **THEN** 详情面板显示"编辑"和"删除"按钮

### Requirement: Action buttons have appropriate size

节点详情面板的编辑和删除按钮 SHALL 具有足够大的点击区域，便于用户操作。

#### Scenario: Buttons are easily clickable
- **WHEN** 用户查看节点详情面板
- **THEN** 编辑和删除按钮的尺寸足够大（至少 32x32 像素点击区域）

#### Scenario: Button icons are visible
- **WHEN** 用户查看操作按钮
- **THEN** 按钮内的图标清晰可见，与按钮尺寸匹配
