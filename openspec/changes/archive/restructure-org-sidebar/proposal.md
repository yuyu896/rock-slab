## Why

当前组织架构侧边栏完全基于 User 自引用 `leader` 字段构建人员树，无法体现「集团→区域→组」的组织层级关系。用户需要在侧边栏看到一个与实际行政架构匹配的层级树：集团→行政经理+区域→行政主管+行政组→行政组长和组员。

## What Changes

- 新增后端 **Team（行政组）** 模型，包含组名、所属区域、组长（leader）等字段
- User 模型新增 `team` 外键，指向所属行政组
- **BREAKING**: 侧边栏树结构从纯人员 `leader` 自引用树改为组织架构层级树：集团（固定顶级）→ 区域/行政经理 → 行政主管/行政组 → 行政组长/组员
- 前端侧边栏渲染逻辑重写：按「区域→组→人员」层级展示，而非扁平 leader 链
- 组织架构标签页详情面板适配新层级结构
- 区域和分公司管理模块保留现有功能不变

## Capabilities

### New Capabilities
- `team-management`: 行政组（Team）的 CRUD 管理——创建、编辑、删除行政组，分配组长和组员，归属到区域下

### Modified Capabilities
- `personnel-management`: 人员管理增加 `team` 字段关联，侧边栏展示逻辑从 leader 自引用树改为组织架构层级树

## Impact

- **后端**: `organizations` app 新增 Team 模型、序列化器、视图集；User 模型新增 `team` FK；数据库迁移
- **前端**: `Organization.vue` 侧边栏树构建逻辑完全重写；新增行政组管理 CRUD UI；类型定义新增 Team 接口；API 层新增 team 接口调用
- **API**: 新增 `/api/teams/` 端点；User API 响应新增 `team` 字段
- **数据库**: 新建 `organizations_team` 表；`users_user` 表新增 `team_id` 列
