## ADDED Requirements

### Requirement: 系统预设头像
系统 SHALL 提供 10 个简约几何风格的预设头像，以 SVG 形式内联渲染。每个预设头像 SHALL 有唯一标识符（如 `geo-1` 至 `geo-10`），并使用不同的配色方案。

#### Scenario: 显示预设头像网格
- **WHEN** 用户打开面板的头像管理区
- **THEN** 显示 10 个预设头像的网格布局（一行 5 个，共两行），每个头像为 48px 圆形

### Requirement: 选择预设头像
用户 SHALL 能点击预设头像进行选择。选中后 SHALL 立即应用该头像，同时清除用户已有的自定义上传头像。

#### Scenario: 选择预设头像
- **WHEN** 用户点击某个预设头像
- **THEN** 该头像被选中（显示选中边框），面板顶部用户信息卡片和侧边栏头像同步更新为该预设头像，后端保存 system_avatar 标识并清除自定义头像

#### Scenario: 预设头像已选中时再次点击
- **WHEN** 用户点击当前已选中的预设头像
- **THEN** 无变化（不触发重复请求）

### Requirement: 自定义头像上传
用户 SHALL 能通过"自定义上传"按钮上传自定义头像。上传自定义头像 SHALL 清除 system_avatar 字段。自定义上传 SHALL 保持现有格式（JPG/PNG/WebP）和大小（2MB）限制。

#### Scenario: 上传自定义头像
- **WHEN** 用户点击"自定义上传"按钮并选择一张合法图片
- **THEN** 弹出预览和确认操作，确认后上传图片，清除 system_avatar 字段，头像更新为自定义图片

#### Scenario: 上传文件超过限制
- **WHEN** 用户选择的文件超过 2MB 或格式不支持
- **THEN** 显示错误提示，不上传

### Requirement: 头像优先级
头像显示 SHALL 遵循以下优先级：自定义上传头像（avatar）> 系统预设头像（system_avatar）> 姓名首字母。当存在自定义头像时 SHALL 显示自定义头像，忽略 system_avatar。

#### Scenario: 同时存在自定义和预设头像
- **WHEN** 用户有自定义上传头像且 system_avatar 字段有值
- **THEN** 显示自定义上传头像，预设头像网格中不显示选中状态

#### Scenario: 仅有预设头像
- **WHEN** 用户没有自定义上传头像但 system_avatar 字段有值
- **THEN** 显示对应的预设头像，预设头像网格中该头像显示选中状态

#### Scenario: 无任何头像
- **WHEN** 用户既没有自定义头像也没有 system_avatar
- **THEN** 显示姓名首字母头像，预设头像网格中无选中状态

### Requirement: 头像管理区布局
头像管理区 SHALL 包含一行"预设头像"标签、预设头像网格（5列×2行）和"自定义上传"按钮。自定义上传按钮 SHALL 显示在网格末尾或下方。

#### Scenario: 头像管理区正常显示
- **WHEN** 用户打开面板
- **THEN** 头像管理区显示"选择头像"标签，下方为 10 个预设头像网格（5列×2行），网格末尾有一个带"+"图标的上传按钮

### Requirement: 后端 system_avatar 字段
User 模型 SHALL 新增 `system_avatar` 字段（CharField，max_length=20，可为空，默认为空）。该字段存储预设头像标识符。后端 SHALL 提供设置 system_avatar 的 API 端点。

#### Scenario: 设置系统预设头像
- **WHEN** 用户通过 API 设置 system_avatar 为有效标识符
- **THEN** 后端保存 system_avatar 值，同时清除 avatar（自定义头像文件），返回更新后的用户数据

#### Scenario: 设置无效标识符
- **WHEN** 用户通过 API 设置 system_avatar 为不在预定义列表中的值
- **THEN** 后端返回 400 错误

### Requirement: 预设头像在侧边栏和组织架构中的展示
预设头像 SHALL 在侧边栏用户卡片、用户面板顶部卡片和组织架构页面的人员头像中统一使用 SVG 渲染。

#### Scenario: 侧边栏显示预设头像
- **WHEN** 用户选择了预设头像且无自定义头像
- **THEN** 侧边栏底部用户卡片显示对应的预设头像 SVG（36px）

#### Scenario: 组织架构页面显示预设头像
- **WHEN** 组织架构页面展示某个选择了预设头像的用户
- **THEN** 该用户头像位置显示对应的预设头像 SVG
