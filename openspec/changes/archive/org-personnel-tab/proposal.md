## Why

组织架构模块目前没有独立的人员管理标签页。人员的新增、编辑、删除操作只能通过侧边栏树的弹窗进行，缺少统一的列表视图来搜索、筛选和批量管理人员。

## What Changes

- 新增"人员管理"标签页，与组织架构、区域管理、分公司管理、行政组同级
- 标签页内展示人员表格，包含搜索框和角色/区域/状态筛选器
- 表格列：姓名、手机号、角色、所属区域、所属分公司、直属上级、状态、操作
- 操作列包含编辑和删除按钮，状态列包含状态开关
- 顶部提供"新增人员"按钮
- `activeTab` 类型扩展，新增 `'personnel'` 选项

## Capabilities

### New Capabilities

（无——人员管理的完整需求已在 `personnel-management` 规格中定义）

### Modified Capabilities

- `personnel-management`: 将已有的规格需求实现为标签页视图（此前规格已定义但前端未实现对应标签页）

## Impact

- `frontend/src/views/Organization.vue`：新增标签页按钮、标签页内容区域、`activeTab` 类型扩展
- 后端 API 无需变更（`/api/users/` 已有完整 CRUD）
