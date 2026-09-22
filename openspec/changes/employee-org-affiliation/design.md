## Context

User 组织归属现状：仅 `branch` FK（可空），区/组沿 branch→team→region 派生（migration 0006 曾删除平铺 org FK 收敛为 branch 单源）。人员事实：轮空员工（组长、区负责人）有区组归属无分公司；组织架构页移动弹窗（Organization.vue `confirmMove`）强制 branch 必选。权限口诀"任命定范围"已覆盖范围问题，本变更只解决**归属的记录与展示**。

## Goals / Non-Goals

**Goals:**
- 归属可表达三种节点之一（或无归属），单源存储不重复
- 移动员工/编辑表单按三态可选操作，每层可"到此为止"
- 通讯录与组织架构页对无分公司员工正确显示区/组

**Non-Goals:**
- 不改数据范围/权限（resolve_user_scope、ManagementScope、任命体系原样）
- 不做批量补挂存量轮空人员（上线后人工/脚本按人员表补，另行处理）
- 不改组织树本身的节点管理（增删改区/组/分公司）

## Decisions

| 决定 | 理由 |
|------|------|
| User 加可空 region/team FK + CheckConstraint（branch/team/region 至多一个非空） | 镜像 ManagementScope 的节点三选一模型；挂分公司者 team/region 必空、沿树派生，铁律 1 不破 |
| 存"最深的实际归属"：挂组存 team（region 派生），挂区存 region | 与人员表口径一致（轮空行=区+组，组是更精确节点；区级轮空才存 region） |
| serializer 层互斥校验（接 branch 同时传 team/region → 400） | DB 约束兜底 + API 友好报错，双保险 |
| 移动弹窗交互：级联选中某层后按钮文案随层变化（"移到大区X"/"移到X组"/"移到X分公司"），选深层自动清浅层 | 每层可确认 + 互斥可视化，避免歧义提交 |
| team_name/region_name 派生顺序：直属节点优先，否则沿 branch 树派生 | branch 用户响应不变（兼容既有前端），新字段新增输出 |
| 前端 User 类型加 `team`/`region` 可空字段，组织架构页员工表新增"归属"列合并展示 | 列表一列看懂三态，替代现在"组名列"对无分公司者的空白 |

## Risks / Trade-offs

- **模型回摆风险**：0006 曾删平铺 FK，本变更以"至多一个"约束回归三节点表达——不是回到冗余双存（派生链保留单一事实源），在提案/注释中写明动机防止后人误判
- SQLite/PG 双库约束：CheckConstraint 两端一致，无 min(uuid) 类聚合，无迁移坑
- 归属与范围解耦可能造成"挂到区却看不到区数据"的疑惑——文档口径：归属=组织身份展示，范围=任命/授权；如需范围找管理员授权
- 前端兼容：旧客户端只认 branch，新字段为增量，不破坏
