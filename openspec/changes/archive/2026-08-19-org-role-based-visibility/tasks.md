## 组织架构角色可见性 — 任务清单

### 角色权限控制

- [ ] T1: 在 `Organization.vue` 引入 `usePermission`，获取 `hasMinRole`
- [ ] T2: 标签页导航增加 `v-if="hasMinRole('manager')"` 条件，隐藏"区域管理"、"分公司管理"、"行政组"标签（supervisor 及以下不可见）
- [ ] T3: 对应标签页的内容区域也增加同样的权限守卫，防止直接切换到隐藏标签页

### 侧边栏调整

- [ ] T4: 移除侧边栏工具栏中的"新增人员"按钮（`<button class="toolbar-btn primary" @click="addItem('users')">`）

### 人员数量修复

- [ ] T5: 新增 `countPersons(node: OrgTreeNode)` 递归函数，统计节点下所有 person 类型节点数
- [ ] T6: 区域节点的 `<span class="node-count">` 改用 `countPersons(child)` 替换 `child.children.length`
- [ ] T7: 行政组节点的 `<span class="node-count">` 改用 `countPersons(subChild)` 替换 `subChild.children.length`

### 侧边栏展开交互优化

- [ ] T8: 区域节点：移除箭头按钮的 `@click.stop` 事件，保留整行 `@click="toggleExpand"` 不变
- [ ] T9: 行政组节点：`node-content` 的 `@click` 从 `selectNode` 改为 `toggleExpand`，移除箭头的 `@click.stop`
- [ ] T10: 未归属人员节点（顶层 team）：同 T9 处理，整行点击展开，箭头纯装饰

### 验证

- [ ] T11: 以 admin/manager 登录，确认全部 5 个标签页可见
- [ ] T12: 以 supervisor/leader/staff 登录，确认仅"组织架构"和"人员管理"可见
- [ ] T13: 确认侧边栏区域/行政组节点人数显示正确
- [ ] T14: 确认点击区域/行政组节点整行可展开收起，箭头不可点击
