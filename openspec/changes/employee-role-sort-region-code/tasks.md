## 1. 员工按职级排序

- [x] 1.1 `orgTree.ts` 新增 `sortEmployeesByRole(users)`：按 `ROLE_LEVELS[role]` 升序、同职级按 `name` 升序（import `ROLE_LEVELS` from constants）
- [x] 1.2 `employees` computed 在 `filterEmployeesByNode` 后调用 `sortEmployeesByRole`
- [x] 1.3 单元测试：员工按职级排序（admin 在 director 前、director 在 manager 前 …；同职级按姓名）

## 2. 区域节点显示编码

- [x] 2.1 组织树区域节点 label 改为「名称（编码）」（如「华东区域（HD）」）

## 3. 验证与部署

- [x] 3.1 `npm run build` + `npm run test`（26 passed）
- [ ] 3.2 部署（仅前端 build + nginx reload）
- [ ] 3.3 线上验证：点「启航集团」时总监/经理/管理员在最上层；区域节点显示编码
