## Why

现有组织架构模块两个问题：(1) 分散在 5 个 tab（组织架构图 / 区域 / 分公司 / 行政组 / 人员），管理员多 tab 切换繁琐；(2) 数据上「分公司」和「行政组」都直属区域（并列），无法表达**真实的「行政组下辖多个分公司」管理关系**。

本次：(1) **后端调整数据模型**——分公司隶属行政组（`Branch.team` FK），建立 区域→行政组→分公司 的真实层级；(2) **前端整合为单页面**——左侧组织树按新层级导航，右侧集中显示员工列表与统一操作栏，删除分散 tab。

## What Changes

### A. 后端：分公司隶属行政组
- **Branch 增加 `team` 外键**（所属行政组，`null=True, on_delete=SET_NULL`），分公司隶属行政组。
- **数据迁移**：新增字段（允许 null）；现有分公司 `team=null`（无历史归属信息，不自动回填），上线后由管理员在 UI 逐步分配。
- Branch 的 serializer / API：创建、编辑分公司支持 `team` 字段。
- 层级关系确立：**Region → Team（行政组，region 下）→ Branch（分公司，team 下）**。

### B. 前端：组织架构单页面
- **删除**独立的 区域 / 分公司 / 行政组 / 人员管理 tab，整合为单一页面。
- **左侧组织树**：按 **区域 → 行政组 → 分公司** 层级展现（沿用现有 orgchart 视觉风格，层级更新为新结构）。
- **右侧主区**（选中节点后）：
  - **顶部栏**：左 = 选中组织名称 + 人数（如「xx 行政组（12 人）」）；右 = **按层级动态**操作——选中区域 → 编辑区域 + 新增行政组；选中行政组 → 编辑行政组 + 新增分公司；选中分公司 → 编辑分公司。
  - **员工操作栏**：创建 / 移动 / 删除员工。
  - **员工列表**：姓名、职务、所属组织、账号（手机号）、所属分公司。
  - **点击员工** → 右侧切换为编辑表单（带返回）。
- **主侧边栏**（系统导航）不变。

## Capabilities

### New Capabilities

- `unified-organization-page`: 组织架构单页面 + 分公司隶属行政组的数据模型（区域→行政组→分公司层级）；左侧树导航 + 右侧员工列表/编辑 + 统一组织/员工操作栏。

### Modified Capabilities

（无。）

## Impact

- **后端**：`apps/organizations/models.py`（Branch 加 `team` FK）+ 新迁移；`organizations/serializers.py`（Branch 序列化加 team）；可能调整 Branch 校验（team 与 region 一致性）。
- **前端**：`views/Organization.vue` 大幅重构 + 拆子组件（OrgTree / EmployeeList / EmployeeEditForm / MoveEmployeeDialog / OrgActionBar）；树层级更新为 区域→行政组→分公司。
- **数据**：现有分公司 `team=null`，需管理员逐步分配（迁移不回填）。
- **风险**：数据模型改动（迁移）+ 前端大重构；需回归组织/员工全流程 + 迁移在生产正确执行。
- **部署**：前后端都改，需 `deploy.sh`（含 migrate）。
