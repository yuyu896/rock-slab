## 1. 后端

- [x] 1.1 新建 `apps/suppliers/`：Supplier 模型（名称全局唯一/联系人/电话，UUIDModel+TimestampedModel）、序列化器、ViewSet（读=IsAuthenticated，写=IsAdminUser）、urls `/api/suppliers`，注册 INSTALLED_APPS
- [x] 1.2 migration（纯建表）+ 后端用例：CRUD、重名 400、非 admin 写 403、登录读 200
- [x] 1.3 后端 pytest 全量绿

## 2. 前端

- [x] 2.1 `api/suppliers.ts`：getSuppliers（选项）/create/update/remove
- [x] 2.2 `views/SupplierManage.vue` 照 DepartmentManage 形态（表格：名称/联系人/电话 + 新增/编辑/删除）；路由 `/suppliers`（requiresAdmin）+ 侧边栏组织架构组·部门字典下方「供应商字典」
- [x] 2.3 `TransferLinesEditor.vue` 供应商单元格改 `<select>`（选项来自字典，空字典显示"暂无供应商"占位不阻断）；行编辑器用例更新
- [x] 2.4 vitest 全量 + `npm run build` 通过

## 3. 收尾

- [x] 3.1 拆 feat + openspec 两 commit，push
- [ ] 3.2 生产部署后 admin 初始化供应商字典（按实际供应商清单录入）
- [x] 3.3 手验：admin 维护字典；经办人建单下拉可选；老单/导入不受影响（2026-09-22 用户验证通过）
