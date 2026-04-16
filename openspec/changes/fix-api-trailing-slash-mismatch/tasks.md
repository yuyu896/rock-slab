# 任务清单

## 问题诊断

### 现象
- 前端登录成功后弹出乱码错误提示
- 区域管理、分公司管理等功能无法正常使用
- 浏览器控制台显示 `POST http://localhost:3000/api/xxx 404 (Not Found)`

### 根因分析
1. 后端 `rock_slab/urls.py` 配置要求 API 路径带尾斜杠：
   ```python
   path('api/assets/', include('apps.assets.urls')),
   ```
2. 后端 `settings/base.py` 设置 `APPEND_SLASH = False`，禁用自动重定向
3. 前端 API 文件调用时不带尾斜杠：
   ```typescript
   return request.get('/api/assets')  // 缺少尾斜杠
   ```
4. 请求返回 404 HTML 页面，`handleApiError()` 将 HTML 当 JSON 处理产生乱码

### 已修复文件
- `frontend/src/api/auth.ts` ✅
- `frontend/src/api/regions.ts` ✅
- `frontend/src/api/branches.ts` ✅

### 待修复文件
- `frontend/src/api/assets.ts` ❌
- `frontend/src/api/users.ts` ❌
- `frontend/src/api/categories.ts` ❌
- `frontend/src/api/transfers.ts` ❌
- `frontend/src/api/inventories.ts` ❌
- `frontend/src/api/reports.ts` ❌
- `frontend/src/api/notifications.ts` ❌
- `frontend/src/api/audit.ts` ❌

---

## 实施任务

### Task 1: 修复 assets.ts ✅
- 文件：`frontend/src/api/assets.ts`
- 修改内容：所有 URL 添加尾斜杠
- 变更：
  - `/api/assets` → `/api/assets/`
  - `/api/assets/${id}` → `/api/assets/${id}/`
  - `/api/assets/import` → `/api/assets/import/`
  - `/api/assets/export` → `/api/assets/export/`

### Task 2: 修复 users.ts ✅
- 文件：`frontend/src/api/users.ts`
- 修改内容：所有 URL 添加尾斜杠

### Task 3: 修复 categories.ts ✅
- 文件：`frontend/src/api/categories.ts`
- 修改内容：所有 URL 添加尾斜杠

### Task 4: 修复 transfers.ts ✅
- 文件：`frontend/src/api/transfers.ts`
- 修改内容：所有 URL 添加尾斜杠

### Task 5: 修复 inventories.ts ✅
- 文件：`frontend/src/api/inventories.ts`
- 修改内容：所有 URL 添加尾斜杠

### Task 6: 修复 reports.ts ✅
- 文件：`frontend/src/api/reports.ts`
- 修改内容：所有 URL 添加尾斜杠

### Task 7: 修复 notifications.ts ✅
- 文件：`frontend/src/api/notifications.ts`
- 状态：已确认无需修改（已有尾斜杠）

### Task 8: 修复 audit.ts ✅
- 文件：`frontend/src/api/audit.ts`
- 状态：已确认无需修改（已有尾斜杠）

---

## 验证清单

- [x] 前端构建成功
- [x] 登录 API 正常
- [x] 资产 API 正常
- [ ] 登录功能正常，无乱码弹窗
- [ ] 资产列表加载正常
- [ ] 区域管理 CRUD 正常
- [ ] 分公司管理 CRUD 正常
- [ ] 分类管理 CRUD 正常
- [ ] 调拨单据 CRUD 正常
- [ ] 盘点功能正常
- [ ] 报表数据加载正常
- [ ] 通知列表加载正常
- [ ] 审计日志加载正常
