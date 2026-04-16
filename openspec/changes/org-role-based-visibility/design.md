## 组织架构角色可见性 — 技术设计

### 1. 角色权限控制标签页

文件：`frontend/src/views/Organization.vue`

利用已有的 `usePermission` 组合式函数：

```typescript
import { usePermission } from '@/hooks/usePermission'
const { hasMinRole } = usePermission()
```

在标签页导航区域，用 `v-if` 控制可见性：

| 标签页 | admin/manager | supervisor/leader/staff |
|--------|:---:|:---:|
| 组织架构 | 可见 | 可见 |
| 区域管理 | 可见 | 隐藏 |
| 分公司管理 | 可见 | 隐藏 |
| 行政组 | 可见 | 隐藏 |
| 人员管理 | 可见 | 可见（只读） |

判断条件：`hasMinRole('manager')` 为 true 时显示全部标签页。

同时需要在标签页内容区和添加按钮也加上相同的权限判断，防止通过 URL 参数或状态手动切换到被隐藏的标签页。

### 2. 移除侧边栏添加人员按钮

文件：`frontend/src/views/Organization.vue`

侧边栏工具栏（约第 735-743 行）当前有：

```html
<button class="toolbar-btn primary" @click="addItem('users')" title="新增人员">
  ...
</button>
```

直接移除此按钮。侧边栏只保留展示功能（搜索 + 组织架构树），新增人员操作在"人员管理"标签页中已有对应按钮。

### 3. 修复侧边栏人员数量统计

#### 问题分析

**区域节点**（第 813 行）：
```html
<span class="node-count">{{ child.children.length }}</span>
```
`child.children` 包含的是行政主管节点（person 类型）和行政组节点（team 类型），不是人员数量。例如某区域有 1 个主管和 2 个行政组，显示 "3" 而非实际人数 "15"。

**行政组节点**（第 863 行）：
```html
<span class="node-count">{{ subChild.children.length }}</span>
```
`subChild.children` 是该组下通过 `u.team === t.id` 筛选出的成员，但组长可能未关联 team（组长通过 `leader` 字段关联，不是 `team`），导致计数不含组长。

#### 修复方案

新增辅助函数 `countPersons`，递归统计某个节点下所有 `nodeType === 'person'` 的节点数：

```typescript
function countPersons(node: OrgTreeNode): number {
  let count = 0
  if (node.nodeType === 'person') count = 1
  for (const child of node.children) {
    count += countPersons(child)
  }
  return count
}
```

模板中将 `child.children.length` 替换为 `countPersons(child)`。

#### 关于行政组组长的问题

检查 `buildOrgTree` 第 200-201 行：

```typescript
const teamMembers = activeUsers.filter(u => u.team === t.id)
```

如果组长的 `team` 字段未设置为该组 ID，则组长不会出现在 `teamMembers` 中。需要同时检查组长的 `leader` 或 `team` 关联，或者在行政组节点构建时额外包含 `leader === t.leader` 且不在 members 中的用户。但根据当前数据模型，组长的 `team` 字段应该指向该组，如果未指向则是数据录入问题，不需要在代码中额外处理——只需通过递归计数函数统一处理即可。

### 4. 侧边栏节点展开交互优化

#### 当前行为

区域节点（约第 798 行）和行政组节点（约第 845 行）的 `node-content` 上绑定了 `@click="toggleExpand(child.id)"`，但同时箭头按钮也有 `@click.stop="toggleExpand(child.id)"`。问题是部分节点（如区域节点的 `node-content`）只有 `@click="toggleExpand"` 而没有 `@click="selectNode"`，点击行为不一致。

#### 修复方案

统一所有可展开节点（区域、行政组、未归属人员）的交互：

1. **整行点击展开/收起**：将 `node-content` 的点击事件统一为 `@click="toggleExpand(nodeId)"`
2. **箭头改为纯装饰**：移除箭头上的 `@click.stop` 事件，箭头仅通过 CSS class `rotated` 做旋转动画指示当前展开状态
3. **人员节点不受影响**：人员节点的点击行为保持 `@click="selectNode(nodeId)"` 用于选中查看详情

涉及的节点：
- 区域节点：`node-content` 已有 `@click="toggleExpand(child.id)"`，箭头需移除 `@click.stop`
- 行政组节点：`node-content` 已有 `@click="selectNode(subChild.id)"`，需改为 `@click="toggleExpand(subChild.id)"`，箭头需移除 `@click.stop`
- 未归属人员节点（顶层 team）：同上处理
