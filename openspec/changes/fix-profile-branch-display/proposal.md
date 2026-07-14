## Why

个人中心（`UserPanel`）的「所属分公司」显示成一串乱码（实际是分公司的 **UUID 主键**），而非真实分公司名称。根因：`UserSerializer` 把 `branch`/`region` 作为外键直接暴露（DRF 默认序列化为 UUID 主键），前端 `UserPanel` 把 `userInfo.branch`（UUID）当文本渲染 → 看起来像乱码。

## What Changes

- **后端** `UserSerializer` 新增只读 `branch_name`（`SerializerMethodField`，返回 `branch.name`）、`region_name`，随用户接口返回（驼峰渲染为 `branchName`/`regionName`）；保留 `branch`/`region` 外键 id 用于创建/更新写入。
- **前端** `UserPanel` 的「所属分公司」改为显示 `branchName`（头部分公司标签 + 信息区两处）。
- 同步前端 `UserInfo` 类型加 `branchName?`。

## Capabilities

### New Capabilities
- `profile-branch-display`: 用户接口额外返回分公司/区域名称；个人中心显示员工真实分公司名称而非外键 UUID。

### Modified Capabilities
<!-- 无：现有 specs 中不含个人中心/用户序列化的分公司展示 capability。 -->

## Impact

- **后端** `apps/users/serializers.py`：`UserSerializer` 加 `branch_name`/`region_name`。
- **前端** `components/layout/UserPanel.vue`（两处显示）、`types/index.ts`（`UserInfo` 加 `branchName?`）。
- **测试**：`UserSerializer` 返回 `branchName` = 分公司名称；无分公司时为 `None`。
- 无 DB 迁移。
