## 1. 集团虚拟根（树构建）

- [x] 1.1 `NodeType` 增加 `'group'`；`TreeNode` / `SelectedNode` 支持集团根
- [x] 1.2 `orgTree` computed 外包一层集团根节点（`type='group'`, `label='启航集团'`, `children=现有区域树`）
- [x] 1.3 树默认展开集团根（进入页面即看到区域层）

## 2. 集团根显示全员

- [x] 2.1 `filterEmployeesByNode`（`utils/orgTree.ts`）增加 `group` 分支 → 返回所有 users
- [x] 2.2 `nodeCount` 对集团根返回全员数
- [x] 2.3 单元测试：`group` 节点返回全员（含全无归属员工）

## 3. 模板与顶部栏

- [x] 3.1 模板树渲染集团根层（区域之上，可展开/收起）
- [x] 3.2 顶部栏：选中集团根时标题「启航集团」+ 全员人数
- [x] 3.3 集团根节点的操作："+区域"（受 `manage_organizations`）

## 4. 验证与部署

- [x] 4.1 `npm run build` + `npm run test`（25 passed）
- [ ] 4.2 部署 `deploy.sh`（仅前端 build + nginx reload）
- [ ] 4.3 线上验证：点「启航集团」看到全员（含 180男神）；区长在区域节点可见
