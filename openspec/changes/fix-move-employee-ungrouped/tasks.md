## 1. 未分组节点携带 regionId

- [x] 1.1 `TreeNode` 类型增加可选 `regionId` 字段
- [x] 1.2 树构建（`orgTree`）中「未分组」虚拟节点设置 `regionId = 区域id`，`rawId` 保留 `''`
- [x] 1.3 `selectedNode` 状态结构增加 `regionId`；`selectNode` 传递未分组节点的 `regionId`

## 2. 修复未分组员工不可见 bug

- [x] 2.1 `employees` computed 增加未分组分支：`node.type === 'team' && !node.rawId` 时返回该 `regionId` 下 `team=null` 分公司的员工
- [x] 2.2 `nodeCount` 同步增加未分组分支，人数正确
- [x] 2.3 顶部栏对未分组节点的标题/人数正确显示（如「未分组（N 人）」）

## 3. 行政组节点含直属组无分公司员工

- [x] 3.1 `employees` 行政组分支改为：`u.branch ∈ 该组分公司` ∪ `(u.team=该组 且 !u.branch)`
- [x] 3.2 `nodeCount` 行政组分支同步上述并集
- [x] 3.3 验证张三（`branch=null`、有 `team`）在所属行政组节点可见

## 4. 移动弹窗三级级联（分公司必选）

- [x] 4.1 `moveState` 增加 `team` 字段，结构改为 `{ employee, region, team, branch }`
- [x] 4.2 新增行政组下拉：列出所选区域的真实行政组 + 「未分组」选项（value=`''`）
- [x] 4.3 分公司下拉随所选行政组过滤：选真实行政组列该组分公司，选「未分组」列该区域 `team=null` 分公司
- [x] 4.4 `watch` 联动：切换 `region` 清空 `team`+`branch`，切换 `team` 清空 `branch`
- [x] 4.5 `confirmMove` 保持同步语义：`team=target.team`、`region=target.region`
- [x] 4.6 移除/调整原只读「将归属行政组」提示（行政组已可选）

## 5. 测试

- [x] 5.1 未分组节点选中时员工列表非空、可见
- [x] 5.2 无分公司但有行政组的员工（张三）在所属行政组节点可见
- [x] 5.3 移动弹窗三级级联与联动（切换区域/行政组清空下级）
- [x] 5.4 跨区域移动时 `team`/`region` 正确同步
- [x] 5.5 未分组员工可移动到真实行政组分公司（移出未分组）
- [x] 5.6 员工可移动到未分组分公司（选「未分组」+ `team=null` 分公司，`team` 同步为空）
- [x] 5.7 `nodeCount` 对未分组节点、行政组节点（含直属组员工）人数正确

> 注：5.1/5.2/5.6/5.7 由 `src/tests/utils/orgTree.test.ts` 覆盖（核心过滤逻辑 `filterEmployeesByNode`）；5.3/5.4/5.5 涉及组件交互与 API，待线上/手动验证（见 6.4）。

## 6. 验证与部署

- [x] 6.1 `npm run build`（类型检查通过）
- [x] 6.2 `npm run test`
- [ ] 6.3 部署：仅前端改动，跑 `deploy.sh`（前端 build + nginx reload，无后端 migrate）
- [ ] 6.4 线上验证：未分组员工可见、张三可见、移动三级级联、移动后归属正确
