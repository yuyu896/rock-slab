# 技术设计

## 问题背景

### 错误流程图

```
前端调用                     后端处理                      前端错误处理
   │                            │                              │
   │ GET /api/assets            │                              │
   │ (无尾斜杠)                  │                              │
   ├───────────────────────────►│                              │
   │                            │ URL 匹配失败                 │
   │                            │ (需要 /api/assets/)          │
   │                            │                              │
   │◄───────────────────────────┤                              │
   │ 404 HTML Page              │                              │
   │ (Django debug page)        │                              │
   │                            │                              │
   ├──────────────────────────────────────────────────────────►│
   │                            │       handleApiError()       │
   │                            │       解析 HTML 为 JSON       │
   │                            │       产生乱码输出            │
   │                            │                              │
```

### 根因代码分析

**后端配置 (rock_slab/urls.py)**
```python
urlpatterns = [
    path('api/assets/', include('apps.assets.urls')),  # 带尾斜杠
    # ...
]
```

**后端设置 (rock_slab/settings/base.py)**
```python
APPEND_SLASH = False  # 禁用自动重定向，不匹配直接 404
```

**前端调用 (api/assets.ts)**
```typescript
export function getAssets(params) {
  return request.get('/api/assets', { params })  // 缺少尾斜杠
}
```

**错误处理 (utils/request.ts)**
```typescript
export function handleApiError(error: unknown): string {
  if (axios.isAxiosError(error) && error.response?.data) {
    const data = error.response.data as ApiError  // HTML 被错误地当作 ApiError
    // Object.entries(htmlString) 产生乱码
  }
}
```

---

## 解决方案

### 方案选择

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| A: 前端加尾斜杠 | 修改所有前端 API 文件 | 改动集中，风险低 | 需修改 8 个文件 |
| B: 后端移除尾斜杠 | 修改 urls.py 和 router | 改动少 | 需同步修改前端已修复的 3 个文件 |
| C: 启用 APPEND_SLASH | 设置 APPEND_SLASH=True | 自动处理 | POST 请求无法重定向 |

**选择方案 A**：修改前端 API 文件，添加尾斜杠

### 修改模式

所有 API 文件统一采用以下模式：

```typescript
// 修改前
export function getXxx() {
  return request.get('/api/xxx')
}
export function getXxx(id: string) {
  return request.get(`/api/xxx/${id}`)
}

// 修改后
export function getXxx() {
  return request.get('/api/xxx/')
}
export function getXxx(id: string) {
  return request.get(`/api/xxx/${id}/`)
}
```

---

## 受影响文件详情

### 1. assets.ts (12 处)
| 行号 | 修改前 | 修改后 |
|------|--------|--------|
| 12 | `/api/assets` | `/api/assets/` |
| 16 | `/api/assets/${id}` | `/api/assets/${id}/` |
| 20 | `/api/assets` | `/api/assets/` |
| 24 | `/api/assets/${id}` | `/api/assets/${id}/` |
| 28 | `/api/assets/${id}` | `/api/assets/${id}/` |
| 35 | `/api/assets/import` | `/api/assets/import/` |
| 42 | `/api/assets/export` | `/api/assets/export/` |

### 2. users.ts
- 列表、详情、创建、更新、删除接口

### 3. categories.ts
- 列表、详情、创建、更新、删除、导入、导出接口

### 4. transfers.ts
- 列表、详情、创建、更新、审批接口

### 5. inventories.ts
- 列表、详情、创建、更新、执行、提交接口

### 6. reports.ts
- 统计报表接口

### 7. notifications.ts
- 通知列表、已读标记接口

### 8. audit.ts
- 审计日志列表接口

---

## 测试验证

### 单元测试
无需新增单元测试，现有 API 调用测试应继续通过。

### 集成测试
1. 登录测试：验证登录成功无错误弹窗
2. 资产列表测试：验证列表加载正常
3. CRUD 测试：验证各模块创建、读取、更新、删除操作正常

### 回归测试
- 运行前端构建：`npm run build`
- 验证所有页面功能正常

---

## 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| 遗漏部分 API 调用 | 低 | 全局搜索 `/api/` 确保覆盖完整 |
| 特殊端点格式不同 | 低 | 检查后端 urls.py 确认格式一致 |
| 缓存问题 | 低 | 清除浏览器缓存后测试 |

---

## 实施步骤

1. **备份**：确认当前代码已提交 git
2. **修改**：逐个修改 8 个 API 文件
3. **构建**：运行 `npm run build` 确认无编译错误
4. **测试**：逐项验证 tasks.md 中的验证清单
5. **提交**：创建 commit 记录本次修复
