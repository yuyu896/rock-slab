## 1. 人员管理 - 停用逻辑修复

- [x] 1.1 `PersonnelManager.vue`：状态筛选默认值从 `''`（全部）改为 `'active'`（在职）
- [x] 1.2 `Organization.vue`：人员删除确认文案从"确定删除该人员？此操作不可恢复"改为"确定停用该人员？停用后该人员将无法登录系统"
- [x] 1.3 `PersonnelManager.vue`：删除按钮文案从图标+tooltip 改为显示"停用"文字按钮

## 2. 组织架构 - 列表刷新修复

- [x] 2.1 `Organization.vue`：删除区域/分公司后也清空 `selectedNodeId`（目前只有删除人员时才清空）
- [x] 2.2 `Organization.vue`：团队创建/编辑后同时刷新用户列表（因为 leader 字段变了会影响用户显示）

## 3. 组织架构 - 小问题修复

- [x] 3.1 `TeamManager.vue`：删除未使用的 `getRegionName` 函数（`regions` 不在 props 中，属于死代码）
- [x] 3.2 `OrganizationBranch.vue`：添加分公司列表为空时的空状态提示
- [x] 3.3 `OrganizationRegion.vue`：添加区域列表为空时的空状态提示

## 4. 验证

- [ ] 4.1 手动验证：人员停用后默认列表中消失，可通过筛选查看已停用人员
- [ ] 4.2 手动验证：区域/分公司/团队的创建、编辑、删除、状态切换功能正常
