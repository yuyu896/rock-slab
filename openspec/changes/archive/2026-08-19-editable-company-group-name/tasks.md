## 1. 后端 Company 模型 + API

- [x] 1.1 `organizations/models.py` 新建 `Company`（`name`，继承 `UUIDModel`+`TimestampedModel`，`get_singleton` 取首条）
- [x] 1.2 迁移 + seed（`get_or_create(name='启航集团')`）
- [x] 1.3 `CompanySerializer` + `CompanyView`（`GET /api/company/` 读、`PATCH /api/company/` 改名受 `manage_organizations`）+ URL
- [x] 1.4 后端测试：读取集团名、管理员改名成功、非管理员改名 403

## 2. 前端

- [x] 2.1 新增 `api/company.ts`（`getCompany`、`updateCompany`）
- [x] 2.2 `Organization.vue` 的 `loadAll` 加载 `company`；`orgTree` 根节点 `label = company.name`
- [x] 2.3 顶部栏集团根「编辑集团」操作 + 弹窗改名 → `updateCompany` → 刷新

## 3. 验证与部署

- [x] 3.1 后端 `pytest`（398 passed）+ 前端 `npm run build` + `npm run test`（26 passed）
- [ ] 3.2 部署 `deploy.sh`（migrate + seed + 前端 build）
- [ ] 3.3 线上验证：编辑集团名 → 根节点显示新名；普通用户也看到新名
