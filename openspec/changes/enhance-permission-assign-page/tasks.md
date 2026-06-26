## 1. 后端：`is_all_data` 全部数据授权

- [x] 1.1 `ManagementScope` 新增 `is_all_data` 布尔字段（默认 False，verbose_name='全部数据'）
- [x] 1.2 调整 CheckConstraint 为 `all_data_or_exactly_one_org_node`：（`is_all_data=True 且三节点全空) OR (is_all_data=False 且恰好一个节点)`
- [x] 1.3 新增条件唯一约束 `uniq_user_all_data`：每用户至多一条 `is_all_data=True`
- [x] 1.4 `ManagementScope.clean()` 同步校验"全部数据 与 具体节点互斥"
- [x] 1.5 `makemigrations` 生成 0003 迁移（纯结构，无回填）并应用

## 2. 后端：scope 与序列化器

- [x] 2.1 `ScopeResolver`：admin 之后、节点收集之前，命中 `is_all_data=True` → 返回 `Scope(all=True)`
- [x] 2.2 `ManagementScopeSerializer`：暴露 `is_all_data`/`isAllData`；`validate` 校验互斥 + 重复 `is_all_data` 拦截（返回 400 而非依赖 DB 约束 500）
- [x] 2.3 测试：`is_all_data`→全部范围、覆盖未来分公司、重复拦截、互斥校验、API 重复/互斥返回 400（新增 6 例）

## 3. 前端：员工选择器可搜索

- [x] 3.1 `PermissionAssign.vue` 员工选择改为 `<el-select filterable>`，按姓名/手机号过滤

## 4. 前端：组织节点"全部数据"选项

- [x] 4.1 节点类型新增"整个组织架构（全部数据）"；选中时提交 `{ user, isAllData: true }`
- [x] 4.2 已授权列表中 `is_all_data` 项展示为"整个组织架构（全部数据）"

## 5. 前端：大区覆盖分公司可见

- [x] 5.1 授予时：节点类型为"大区"且选定大区后，展示"含 N 个分公司：…"（前端按 `region` 过滤已加载 branches）
- [x] 5.2 已授权列表：大区类型项展示"大区：X（含 N 个分公司）"

## 6. 验证

- [x] 6.1 后端 `pytest`：权限相关 77 例通过；新增 6 例（模型 + API）；全量 310 通过（仅 4 例预存 openpyxl `vertical='middle'` 失败，与本变更无关）
- [x] 6.2 前端 `npm run build` 通过（类型检查 ✓）
- [x] 6.3 live 冒烟：创建 is_all_data→201、重复→400、与节点互斥→400（已清理测试数据）
