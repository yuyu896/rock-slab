## Why

大量员工（轮空人员，如组长/区负责人本人）没有分公司归属，但有明确的大区、行政组归属（人员表三列：大区/小组/分公司，分公司可为"轮空"）。当前系统 User 只有一个 branch 外键，区域/小组归属全靠 branch→team→region 反推：无分公司的人组织归属完全丢失（通讯录与组织架构页区组列空白）；组织架构页"移动员工"弹窗三级级联强制选到分公司才能确认（`请选择目标分公司`），无法把人挂到"仅大区"或"仅行政组"。

## What Changes

- User 模型新增可空 `region` / `team` 外键，数据库约束 **branch / team / region 至多填一个**（挂分公司的人照旧只存 branch，区组沿树派生——不违反铁律 1"每样信息只存一处"）
- 归属三态可选 + 无归属：挂分公司（现状）｜挂行政组（region 沿 team 派生）｜挂大区；均可为空
- "移动员工"弹窗：区域 → 行政组 → 分公司 三级级联，**每层均可"到此为止"确认**（选区即确认=归属该区；选组确认=归属该组；选分公司=现状行为）；确认目标为更深层时清空浅层互斥
- 用户序列化与展示：`team_name` / `region_name` 改为按实际归属节点派生（branch→team→region 或直属 team/region），通讯录、组织架构页区组列对无分公司员工正常显示
- 员工编辑表单同步：分公司可选基础上增加归属节点选择（与移动弹窗同口径）
- **归属 ≠ 权限**：数据范围仍由任命（区/组/司负责人）与管理授权决定，仅挂到大区不自动获得全区数据范围——本变更不动 resolve_user_scope

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `personnel-management`: 员工组织归属由"分公司单选（可空）"扩展为"分公司/行政组/大区三选一（可空）"；移动员工与编辑表单按三态可选操作；列表展示按实际归属派生大区/组名

## Impact

- 后端：`apps/users/models.py`（+region/team FK + CheckConstraint + migration）、`serializers.py`（字段、互斥校验、派生 team_name/region_name）、`views.py`（无行为变化，校验在 serializer）
- 前端：`views/Organization.vue`（移动弹窗每层可确认、员工列表区组列）、员工编辑表单、`types/index.ts`
- 存量数据：现有 134 账号 branch 之外全空，约束天然满足，无需数据迁移；10 位轮空员工可随后按人员表补挂区/组
- 不影响：resolve_user_scope / DataScopeMixin / 任命与授权体系、台账与单据
