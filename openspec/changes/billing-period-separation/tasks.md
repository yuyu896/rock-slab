# 实施任务清单

## 后端改动

### 任务 1：数据模型改造
**文件**：`backend/apps/reconciliation/models.py`

- [ ] 在 `ReconciliationTask` 模型中新增 `billing_period` 字段（DateField，允许 null）
- [ ] 修改 `Meta.ordering` 为 `['-billing_period', 'supplier__name']`
- [ ] 删除旧约束 `uniq_recon_supplier_period`
- [ ] 新增约束 `uniq_recon_supplier_billing_period`（字段：`supplier`, `billing_period`）

**验收**：模型字段和约束定义正确

---

### 任务 2：创建数据迁移
**文件**：`backend/apps/reconciliation/migrations/xxxx_add_billing_period.py`

- [ ] 新增 `billing_period` 字段（nullable）
- [ ] 编写 `forwards` 函数：从 `ReconciliationOrderRow.accounting_date` 提取月份
- [ ] fallback 逻辑：无订单行时 `billing_period = period`
- [ ] 将 `billing_period` 改为 NOT NULL
- [ ] 删除旧约束 `uniq_recon_supplier_period`
- [ ] 新增约束 `uniq_recon_supplier_billing_period`

**验收**：
- 本地 SQLite 迁移通过
- 存量任务的 `billing_period` 正确填充

---

### 任务 3：修改解析逻辑
**文件**：`backend/apps/reconciliation/services.py`

**3.1 修改 `parse_workbook` 函数**
- [ ] 在返回前提取所有 `accounting_date` 的唯一月份
- [ ] 校验：若包含多个月份 → 抛出 `ValidationError`（带月份列表）
- [ ] 返回值改为 `(parsed, billing_period)` 元组

**3.2 修改金额计算（153 行附近）**
- [ ] 将 `billing_for_period(period, accounting, rent)` 改为 `billing_for_period(billing_period, accounting, rent)`

**验收**：
- 导入包含多个账期的文件报错正确
- 金额计算使用 `billing_period` 而非 `period`

---

### 任务 4：修改导入接口
**文件**：`backend/apps/reconciliation/services.py` 或 `views.py`

**4.1 修改 `_prepare_reconciliation_order` 函数**
- [ ] 解包 `parse_workbook` 返回值为 `parsed, billing_period`
- [ ] 唯一约束检查改为 `filter(supplier=supplier, billing_period=billing_period)`
- [ ] 错误提示包含 `billing_period` 和已存在任务 ID

**4.2 修改 `preview` 接口返回值**
- [ ] 在预览数据中新增 `billing_period` 字段

**4.3 修改 `import` 接口**
- [ ] 创建 `ReconciliationTask` 时传入 `billing_period` 参数

**验收**：
- 导入同供应商不同账期的任务不冲突
- 导入同供应商相同账期的任务报唯一约束错误

---

### 任务 5：序列化器调整
**文件**：相关 serializers 或 views

- [ ] 任务列表序列化增加 `billing_period` 字段
- [ ] 任务详情序列化增加 `billing_period` 字段
- [ ] 预览数据包含 `billing_period` 字段

**验收**：API 返回 JSON 包含 `billingPeriod` 字段

---

## 前端改动

### 任务 6：类型定义
**文件**：`frontend/src/api/reconciliation.ts`

- [ ] `ReconciliationTask` 接口新增 `billingPeriod: string`
- [ ] `ReconciliationImportPreview` 接口新增 `billingPeriod: string`

**验收**：类型定义正确

---

### 任务 7：订单列表页
**文件**：`frontend/src/views/reconciliation/ReconciliationOrders.vue`

- [ ] 筛选表单新增"结算账期"月份选择器
- [ ] 表格新增"结算账期"列
- [ ] 导入预览对话框显示 `billingPeriod`

**验收**：
- 筛选器可按结算账期筛选
- 表格显示对账月份和结算账期两列

---

### 任务 8：差异页
**文件**：`frontend/src/views/reconciliation/ReconciliationDifferences.vue`

- [ ] Banner 信息中新增"结算账期"描述项
- [ ] 确保 `billingPeriod` 正确显示

**验收**：详情页同时显示对账月份和结算账期

---

### 任务 9：付款页
**文件**：`frontend/src/views/reconciliation/ReconciliationPayment.vue`

- [ ] 标题/面包屑使用 `billingPeriod` 而非 `period`
- [ ] 确保付款明细按结算账期分组

**验收**：付款页显示结算账期

---

## 测试验证

### 任务 10：本地测试
- [ ] 后端迁移通过（SQLite）
- [ ] 导入包含多个账期的 Excel 报错正确
- [ ] 导入同供应商不同账期任务成功
- [ ] 导入同供应商相同账期任务报唯一约束错误
- [ ] 金额计算按 `billing_period` 正确
- [ ] 前端类型检查通过（`npm run build`）
- [ ] 前端三个页面显示正确

### 任务 11：生产部署准备
- [ ] 生产迁移脚本测试（PostgreSQL）
- [ ] 备份生产数据库
- [ ] 部署计划：先后端（迁移），再前端

---

## 实施顺序

1. 后端任务 1-2（模型 + 迁移）
2. 后端任务 3-5（逻辑 + 接口）
3. 前端任务 6-9（类型 + 页面）
4. 任务 10（本地测试）
5. 任务 11（生产准备）
