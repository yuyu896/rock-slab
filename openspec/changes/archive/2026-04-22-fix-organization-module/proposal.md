## Why

组织架构模块存在两个问题：
1. 人员管理中"删除"人员后，人员仍显示在列表中——因为后端是软删除（status→inactive），但前端人员列表未过滤 inactive 用户
2. 需要全面验证组织架构模块（区域、分公司、行政组、人员管理）的所有 CRUD 功能是否正常

## What Changes

- 人员管理列表默认只显示 active 状态的用户，inactive 用户通过筛选条件查看
- "删除"操作改为明确的"停用"语义：确认文案改为"停用"、按钮文案改为"停用"
- 停用后的用户在列表中默认隐藏，可通过状态筛选查看
- 全面验证区域/分公司/行政组/人员的创建、编辑、删除、状态切换功能

## Capabilities

### New Capabilities
- `personnel-status-filter`: 人员管理列表的状态筛选逻辑，默认过滤 inactive 用户，"删除"按钮改为"停用"

### Modified Capabilities

## Impact

- **前端**: `Organization.vue` — 人员删除确认文案、`fetchUsers` 过滤逻辑
- **前端**: `PersonnelManager.vue` — 删除按钮文案和样式
- **后端**: 无变更，后端软删除逻辑本身正确
- **现有数据**: 不受影响
