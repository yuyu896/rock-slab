# 对账模块重新设计 实施方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将对账模块从单页全量明细视图重构为"供应商订单 / 序列号差异 / 待付金额"三页协作流程，引入分公司状态汇总层解决 80 家分公司下的性能与可读性问题，新增重新对账与固定结论类型以支撑"补录后重算"的纠正闭环。

**Architecture:** 后端复用现有 `apps/reconciliation` 模型，新增 `branch-summary` 与 `rematch` 两个接口、`conclusion_type` 固定选项字段；前端拆分单文件 `Reconciliation.vue` 为三页 `views/reconciliation/{Orders,Differences,Payment}.vue` + 共享上下文 composable，全局"当前任务"通过 URL query (`?task=<id>`) 在三页间传递。沿用现有 DataScopeMixin 权限模型与 camelCase API 约定。

**Tech Stack:** Django 5.1 + DRF（后端），Vue 3.5 Composition API + TypeScript + Element Plus + Pinia（前端），openpyxl（Excel 解析/导出）。

**Spec:** 本文档即设计书（探讨会结论，2026-11-05）。背景记忆见 `memory/reconciliation-redesign-context.md`。

## Global Constraints

- **品目固定**：对账仅覆盖电脑品目 `A-a00001 / A-a00008 / A-a00011 / A-a00012`（`services.py:ITEM_CODES`），不扩展。
- **唯一写入口纪律**：补录电脑仍走采购入库流转单 + 审批生效，对账模块不直接改台账（铁律 2）。
- **中文字段名**：Django 模型字段沿用中文（`分公司`、`序列号` 等），API 经 djangorestframework-camel-case 转 camelCase。
- **URL 风格**：`trailing_slash=False`，`APPEND_SLASH=False`。
- **权限**：`view_reconciliation` / `manage_reconciliation` / `view_suppliers` 三个操作码；导入需 `manage_reconciliation + view_suppliers`。
- **数据隔离**：`resolve_user_scope(user)` 限制可见分公司范围，非全权账号只能看自己分公司的对账结果。
- **前端类型门禁**：改动提交前必须跑 `npm run build`（vue-tsc），vitest 不查类型。
- **部署铁律**：改动只落本地 + GitHub，禁止触生产；用户本地验证后自行 `deploy.sh`。
- **分页格式**：`{ count, next, previous, results }`，参数 `pageSize`（默认 20，最大 100）。
- **金额精度**：Decimal 两位小数，`CENT = Decimal('0.01')`，`ROUND_HALF_UP`。

## Review Focus

1. **待付金额口径**：差异行"未结论"时金额不计入已确认，"已结案/已有结论"才计入；匹配行始终计入。测试：Task 8 的金额聚合测试。
2. **重新对账幂等性**：`rematch` 复用订单数据生成新版本，不重复创建 issue（`issue_key` 去重）；旧版本不可变。
3. **补录后重新对账时机**：流转单审批生效后才进对账比对；草稿/待审批状态不参与（`审批状态__in=['已通过','已入库']` 已在 `build_comparison` 内）。
4. **80 分公司性能**：`branch-summary` 接口一次聚合返回全部分公司汇总（约 80 行 × 6 列），不返回 comparison 明细行；前端按需拉明细。
5. **归档门禁**：`待确认金额 > 0`（存在未结论差异）时禁止归档，提示"仍有 N 条差异未处理"。

---

## File Structure

### 后端

```
backend/apps/reconciliation/
  models.py              [改] 新增 conclusion_type 字段 + CONCLUSION_CHOICES
  migrations/0004_conclusion_type.py  [新] 迁移
  services.py            [改] 拆 build_comparison；新增 branch_summary / rematch / payment_summary
  views.py               [改] 新增 BranchSummaryView / RematchView / PaymentSummaryView / PaymentExportView
  urls.py                [改] 新增 4 个路由
  tests/                 [新] 新增 test_branch_summary / test_rematch / test_payment
```

### 前端

```
frontend/src/
  views/reconciliation/
    ReconciliationOrders.vue       [新] 页1：供应商订单管理
    ReconciliationDifferences.vue  [新] 页2：分公司状态 + 差异明细
    ReconciliationPayment.vue       [新] 页3：待付金额确认 + 明细表
  composables/
    useReconciliationTask.ts        [新] 共享"当前任务"上下文（URL query ?task=<id> 同步）
  api/
    reconciliation.ts               [改] 新增 branch-summary / rematch / payment 接口
  router/
    index.ts                        [改] 三个子路由 + landing 入口
  components/
    ReconciliationTaskSelector.vue  [新] 三页顶部共享的"供应商+月份"选择 banner
```

### 删除

- `frontend/src/views/Reconciliation.vue`（拆分后移除，路由不再引用）

---

## Task 1: 后端 conclusion_type 字段与迁移

**Files:**
- Modify: `backend/apps/reconciliation/models.py:83-112`（`ReconciliationIssue` 类）
- Create: `backend/apps/reconciliation/migrations/0004_conclusion_type.py`
- Test: `backend/tests/test_reconciliation_conclusion.py`（新建）

**Interfaces:**
- Produces: `ReconciliationIssue.CONCLUSION_CHOICES`（5 项元组常量）、`ReconciliationIssue.conclusion_type` 字段（CharField max_length=32，blank=True，default=''）。后续任务 5/8 依赖此字段判金额口径。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_reconciliation_conclusion.py
import pytest
from apps.reconciliation.models import ReconciliationIssue

@pytest.mark.django_db
class TestConclusionType:
    def test_conclusion_choices_has_five_types(self):
        codes = [code for code, _ in ReconciliationIssue.CONCLUSION_CHOICES]
        assert codes == [
            'system_not_registered', 'serial_corrected',
            'supplier_overbilled', 'supplier_underbilled',
            'period_adjustment',
        ]

    def test_default_empty(self, branch):
        from apps.suppliers.models import Supplier
        from apps.reconciliation.models import ReconciliationTask
        from datetime import date
        supplier = Supplier.objects.create(name='测试供应商')
        task = ReconciliationTask.objects.create(supplier=supplier, period=date(2026, 11, 1))
        issue = ReconciliationIssue.objects.create(
            supplier=supplier, issue_key='k1', issue_type='order_only',
            first_period=task.period, last_period=task.period,
        )
        assert issue.conclusion_type == ''

    def test_invalid_choice_rejected(self):
        from django.core.exceptions import ValidationError
        issue = ReconciliationIssue(
            supplier_id=None, issue_key='x', issue_type='order_only',
            first_period='2026-11-01', last_period='2026-11-01',
            conclusion_type='bogus',
        )
        with pytest.raises(ValidationError):
            issue.full_clean()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_reconciliation_conclusion.py -v`
Expected: FAIL（`conclusion_type` 字段不存在）

- [ ] **Step 3: 在 models.py 的 `ReconciliationIssue` 加字段与常量**

在 `issue_type` 字段下方加 `CONCLUSION_CHOICES`（5 项）与 `conclusion_type = models.CharField(max_length=32, choices=CONCLUSION_CHOICES, blank=True, default='')`。中文 verbose_name 用：系统未登记已补录 / 序列号已纠正 / 供应商多报 / 供应商少报 / 期间调整。

- [ ] **Step 4: 生成迁移**

Run: `cd backend && python manage.py makemigrations reconciliation --name conclusion_type`
Expected: 生成 `0004_conclusion_type.py`

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && pytest tests/test_reconciliation_conclusion.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/reconciliation/models.py backend/apps/reconciliation/migrations/0004_conclusion_type.py backend/tests/test_reconciliation_conclusion.py
git commit -m "feat(reconciliation): 新增差异结论固定类型字段 conclusion_type"
```

---

## Task 2: 后端 branch-summary 接口

**Files:**
- Modify: `backend/apps/reconciliation/services.py`（新增 `build_branch_summary(task, scope)` 函数）
- Modify: `backend/apps/reconciliation/views.py`（新增 `BranchSummaryView`）
- Modify: `backend/apps/reconciliation/urls.py`
- Test: `backend/tests/test_reconciliation_branch_summary.py`（新建）

**Interfaces:**
- Consumes: Task 1 的 `conclusion_type`（判未结论差异）
- Produces: `GET /api/reconciliation/tasks/<id>/branch-summary` 返回 `{ branch_id, branch_name, order_count, matched_count, diff_count, pending_count, month_amount }` 列表；Task 3 前端页2 依赖此接口。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_reconciliation_branch_summary.py
import pytest
from decimal import Decimal
from datetime import date
from apps.reconciliation.models import ReconciliationTask, ReconciliationUploadVersion
from apps.suppliers.models import Supplier

@pytest.mark.django_db
class TestBranchSummary:
    def _task_with_rows(self, branch, supplier=None):
        if supplier is None:
            supplier = Supplier.objects.create(name='供应商A')
        task = ReconciliationTask.objects.create(supplier=supplier, period=date(2026, 11, 1))
        return task

    def test_summary_returns_per_branch_counts(self, admin_user, branch, second_branch):
        # 造一个有两条订单行（分属两分公司）、一条匹配一条仅订单有的版本
        # 断言返回 2 行，各自 order_count=1，分支A matched=1 diff=0，分支B diff=1 pending=1
        ...

    def test_summary_pending_uses_conclusion_type(self, admin_user, branch):
        # 已有 conclusion_type 的差异不计 pending；空 conclusion_type 计 pending
        ...

    def test_summary_scope_filtered(self, staff_user, branch):
        # 非全权账号只返回其 scope 内分公司
        ...
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_reconciliation_branch_summary.py -v`
Expected: FAIL（接口/函数不存在）

- [ ] **Step 3: 实现 `build_branch_summary(task, scope)`**

在 `services.py` 末尾加函数：以 `ReconciliationComparison` 按 `order_row__branch_id`（缺失用 `system_branch_id`）分组聚合 `Count` 与 `Sum('order_row__month_amount')`；`pending_count` = 差异行中 `issue__conclusion_type=''` 且 `issue__status__in=['open','not_recurred']` 的数量；按 scope 过滤（复用现有 `_comparison_queryset_for_scope`）。

- [ ] **Step 4: 实现 `BranchSummaryView` 并注册路由**

在 `views.py` 加 `class BranchSummaryView(ReconciliationPermissionView)`，`get` 返回 `build_branch_summary(task, scope)`；`urls.py` 加 `path('tasks/<uuid:pk>/branch-summary', BranchSummaryView.as_view())`。

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && pytest tests/test_reconciliation_branch_summary.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/reconciliation/services.py backend/apps/reconciliation/views.py backend/apps/reconciliation/urls.py backend/tests/test_reconciliation_branch_summary.py
git commit -m "feat(reconciliation): 新增 branch-summary 接口，按分公司聚合差异状态"
```

---

## Task 3: 后端 rematch 重新对账接口

**Files:**
- Modify: `backend/apps/reconciliation/services.py`（新增 `rematch_task(task, user)`）
- Modify: `backend/apps/reconciliation/views.py`（新增 `RematchView`）
- Modify: `backend/apps/reconciliation/urls.py`
- Test: `backend/tests/test_reconciliation_rematch.py`（新建）

**Interfaces:**
- Consumes: 现有 `build_comparison`（不重传文件，复用当前版本的 `ReconciliationOrderRow`）
- Produces: `POST /api/reconciliation/tasks/<id>/rematch` 返回新版本号；版本号 = 现有最大 +1；issue 按 `issue_key` 复用（不重复创建）；Task 5 前端"重新对账"按钮依赖此接口。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_reconciliation_rematch.py
import pytest
from apps.reconciliation.services import rematch_task

@pytest.mark.django_db
class TestRematch:
    def test_rematch_creates_new_version_reusing_orders(self, admin_user, branch, supplier):
        # 建一个已导入版本 v1，补一台系统实例后调 rematch → v2，差异减少
        # 断言 task.current_version.version_number == 2
        # 断言 v2 的 order_row 数 == v1（复用）
        ...

    def test_rematch_idempotent_issues(self, admin_user, branch, supplier):
        # 同一 issue_key 跨版本不重复创建（count 不翻倍）
        ...

    def test_rematch_archived_rejected(self, admin_user, branch, supplier):
        # 已归档任务调 rematch → ValidationError
        ...

    def test_rematch_permission(self, staff_user, branch, supplier):
        # 非 manage_reconciliation 账号 403
        ...
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_reconciliation_rematch.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 `rematch_task(task, user)`**

在 `services.py` 加函数（`@transaction.atomic`）：校验 `task.status != archived`；取 `task.current_version`，复制其 `order_rows` 到新 `ReconciliationUploadVersion`（version_number+1，file 字段沿用旧文件路径）；调 `build_comparison(task, new_version)`；更新 `task.current_version`；返回新版本号。**不重新解析 Excel**，只复用 `ReconciliationOrderRow` 数据。

- [ ] **Step 4: 实现 `RematchView` 并注册路由**

`views.py` 加 `class RematchView(ReconciliationImportPermissionView)`，`post` 调 `rematch_task` 并 `@audit_log`；`urls.py` 加 `path('tasks/<uuid:pk>/rematch', RematchView.as_view())`。

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && pytest tests/test_reconciliation_rematch.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/reconciliation/services.py backend/apps/reconciliation/views.py backend/apps/reconciliation/urls.py backend/tests/test_reconciliation_rematch.py
git commit -m "feat(reconciliation): 新增 rematch 接口，复用订单数据重跑比对"
```

---

## Task 4: 后端 payment-summary 与 payment-export 接口

**Files:**
- Modify: `backend/apps/reconciliation/services.py`（新增 `build_payment_summary(task, scope)`）
- Modify: `backend/apps/reconciliation/views.py`（新增 `PaymentSummaryView`、改 `ReconciliationExportView` 支持付款明细）
- Modify: `backend/apps/reconciliation/urls.py`
- Test: `backend/tests/test_reconciliation_payment.py`（新建）

**Interfaces:**
- Consumes: Task 1 `conclusion_type`（判已确认 vs 待确认）
- Produces: `GET /api/reconciliation/tasks/<id>/payment` 返回 `{ confirmed_amount, pending_amount, total_amount, can_archive, rows:[...] }`；Task 6 前端页3 依赖。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_reconciliation_payment.py
import pytest
from decimal import Decimal

@pytest.mark.django_db
class TestPaymentSummary:
    def test_matched_rows_in_confirmed(self, admin_user, branch, supplier):
        # 匹配行金额计入 confirmed
        ...

    def test_unconcluded_diff_in_pending(self, admin_user, branch, supplier):
        # 未结论差异行计入 pending，不计 confirmed
        ...

    def test_concluded_diff_in_confirmed(self, admin_user, branch, supplier):
        # conclusion_type 非空的差异行计入 confirmed
        ...

    def test_can_archive_requires_zero_pending(self, admin_user, branch, supplier):
        # pending=0 时 can_archive=True
        ...
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_reconciliation_payment.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 `build_payment_summary(task, scope)`**

`confirmed_amount` = 匹配行 `month_amount` 之和 + 差异行中 `issue__conclusion_type != ''` 的 `month_amount` 之和；`pending_amount` = 差异行中 `issue__conclusion_type == ''` 且 `issue__status__in=['open','not_recurred']` 的 `month_amount` 之和；`can_archive = pending_amount == 0`；`rows` 为全部 comparison 行的付款明细（序列号/分公司/内部编号/起租/记账/天数/月租金/本月金额/计费状态）。

- [ ] **Step 4: 实现 `PaymentSummaryView` + 注册路由**

`urls.py` 加 `path('tasks/<uuid:pk>/payment', PaymentSummaryView.as_view())`。同时给 `ReconciliationExportView` 加 `?type=payment` 分支导出付款明细表（列：序列号/分公司/内部编号/起租日期/记账日期/计费天数/月租金/本月金额/计费状态/结论）。

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && pytest tests/test_reconciliation_payment.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/reconciliation/services.py backend/apps/reconciliation/views.py backend/apps/reconciliation/urls.py backend/tests/test_reconciliation_payment.py
git commit -m "feat(reconciliation): 新增待付金额聚合与付款明细导出"
```

---

## Task 5: 前端共享上下文 composable 与任务选择器

**Files:**
- Create: `frontend/src/composables/useReconciliationTask.ts`
- Create: `frontend/src/components/ReconciliationTaskSelector.vue`
- Test: `frontend/src/tests/composables/useReconciliationTask.test.ts`（新建）

**Interfaces:**
- Consumes: 现有 `getReconciliationTasks`
- Produces: `useReconciliationTask()` 返回 `{ currentTaskId, currentTask, setTask, clearTask, taskOptions, loadTaskOptions }`；`currentTaskId` 与 URL `?task=<id>` 双向同步；三页均通过此 composable 获取当前任务。

- [ ] **Step 1: 写失败测试**

```typescript
// frontend/src/tests/composables/useReconciliationTask.test.ts
import { setActivePinia, createPinia } from 'pinia'
import { useReconciliationTask } from '@/composables/useReconciliationTask'

describe('useReconciliationTask', () => {
  beforeEach(() => setActivePinia(createPinia()))
  it('exposes currentTaskId ref', () => {
    const { currentTaskId } = useReconciliationTask()
    expect(currentTaskId.value).toBe('')
  })
  it('setTask updates currentTaskId', () => {
    const { currentTaskId, setTask } = useReconciliationTask()
    setTask('abc')
    expect(currentTaskId.value).toBe('abc')
  })
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/tests/composables/useReconciliationTask.test.ts`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现 composable**

用 `ref` 存 `currentTaskId`，初始化从 `route.query.task` 读；`watch(currentTaskId)` 时 `router.replace({ query: { ...route.query, task: id } })`；`setTask(id)` 设值并触发 `getReconciliationTask(id)` 加载详情。导出单例（模块级 ref，跨组件共享）。

- [ ] **Step 4: 实现 `ReconciliationTaskSelector.vue`**

顶部 banner 组件：供应商下拉 + 月份下拉 + 当前版本提示；`@change` 调 `setTask`；无任务时显示"请先在订单页导入"。

- [ ] **Step 5: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/tests/composables/useReconciliationTask.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/composables/useReconciliationTask.ts frontend/src/components/ReconciliationTaskSelector.vue frontend/src/tests/composables/useReconciliationTask.test.ts
git commit -m "feat(reconciliation): 新增共享当前任务上下文 composable 与选择器"
```

---

## Task 6: 前端页1 供应商订单

**Files:**
- Create: `frontend/src/views/reconciliation/ReconciliationOrders.vue`
- Modify: `frontend/src/api/reconciliation.ts`（已有接口够用，仅类型补充）
- Test: `frontend/src/tests/views/ReconciliationOrders.test.ts`（新建）

**Interfaces:**
- Consumes: Task 5 composable；现有 `getReconciliationTasks / previewReconciliationOrder / importReconciliationOrder`
- Produces: 路由 `/reconciliation/orders`；管理订单导入与历史版本查看。

- [ ] **Step 1: 写失败测试**

测试渲染组件、点击"导入订单"打开 dialog、提交后调 `importReconciliationOrder` 并 `setTask`。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/tests/views/ReconciliationOrders.test.ts`
Expected: FAIL

- [ ] **Step 3: 实现 `ReconciliationOrders.vue`**

复用现有 `Reconciliation.vue` 的导入 dialog 逻辑（`openImportDialog / previewImport / submitImport`）；顶部放 `ReconciliationTaskSelector`；列表展示该供应商×月份的版本历史（调用 `getReconciliationTask` 的 `versions` 字段）；导入成功后 `setTask(data.id)` 跳页2。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/tests/views/ReconciliationOrders.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/reconciliation/ReconciliationOrders.vue frontend/src/api/reconciliation.ts frontend/src/tests/views/ReconciliationOrders.test.ts
git commit -m "feat(reconciliation): 页1 供应商订单管理"
```

---

## Task 7: 前端页2 序列号差异（分公司状态 + 明细）

**Files:**
- Create: `frontend/src/views/reconciliation/ReconciliationDifferences.vue`
- Modify: `frontend/src/api/reconciliation.ts`（加 `getBranchSummary`、`rematchTask`）
- Test: `frontend/src/tests/views/ReconciliationDifferences.test.ts`（新建）

**Interfaces:**
- Consumes: Task 5 composable；Task 2 `branch-summary` 接口；Task 3 `rematch` 接口
- Produces: 路由 `/reconciliation/differences`；分公司状态列表 + 按需展开差异明细 + 结论下拉 + 重新对账按钮。

- [ ] **Step 1: 写失败测试**

测试：渲染分公司列表（mock `getBranchSummary`）；点击分公司行展开加载明细（mock `getReconciliationTask?branch=`）；结论下拉变更触发 `updateReconciliationIssue`；"重新对账"按钮调 `rematchTask` 后刷新。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/tests/views/ReconciliationDifferences.test.ts`
Expected: FAIL

- [ ] **Step 3: 实现 `ReconciliationDifferences.vue`**

顶部 `ReconciliationTaskSelector` + KPI 条（匹配率/差异数/待结论数）；分公司竖向列表（`el-table`，行：状态色块/分公司名/订单台数/差异数/待结论/本月金额/展开箭头）；行展开时按 `?branch=<id>` 拉 comparison 明细（复用 `getReconciliationTask`）；明细列含结论下拉（5 选项 `CONCLUSION_CHOICES`）+ 备注；顶部"重新对账"按钮调 `rematchTask` 后重新拉 `branch-summary`。状态色：🔴 pending>0 / 🟡 diff>0 且 pending=0 / ✅ diff=0。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/tests/views/ReconciliationDifferences.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/reconciliation/ReconciliationDifferences.vue frontend/src/api/reconciliation.ts frontend/src/tests/views/ReconciliationDifferences.test.ts
git commit -m "feat(reconciliation): 页2 序列号差异工作台（分公司状态+明细）"
```

---

## Task 8: 前端页3 待付金额

**Files:**
- Create: `frontend/src/views/reconciliation/ReconciliationPayment.vue`
- Modify: `frontend/src/api/reconciliation.ts`（加 `getPaymentSummary`、`exportPayment`）
- Test: `frontend/src/tests/views/ReconciliationPayment.test.ts`（新建）

**Interfaces:**
- Consumes: Task 5 composable；Task 4 `payment` 接口与导出
- Produces: 路由 `/reconciliation/payment`；已确认/待确认金额 + 付款明细表 + 归档门禁。

- [ ] **Step 1: 写失败测试**

测试：渲染金额汇总（mock `getPaymentSummary` 返回 confirmed/pending/total）；待确认 > 0 时归档按钮禁用且提示；明细表行数与 mock 一致；导出按钮触发 blob 下载。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/tests/views/ReconciliationPayment.test.ts`
Expected: FAIL

- [ ] **Step 3: 实现 `ReconciliationPayment.vue`**

顶部 `ReconciliationTaskSelector` + 金额卡（已确认 ¥ / 待确认 ¥ / 本月应计 ¥）；`can_archive=false` 时归档按钮 disabled + tooltip "仍有 N 条差异未处理"；明细 `el-table`（列：序列号/分公司/内部编号/起租日期/记账日期/计费天数/月租金/本月金额/计费状态/结论）；导出按钮调 `exportReconciliationTask(id, 'payment')`。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/tests/views/ReconciliationPayment.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/reconciliation/ReconciliationPayment.vue frontend/src/api/reconciliation.ts frontend/src/tests/views/ReconciliationPayment.test.ts
git commit -m "feat(reconciliation): 页3 待付金额确认与明细表"
```

---

## Task 9: 路由与导航整合 + 清理旧单页

**Files:**
- Modify: `frontend/src/router/index.ts:94`（拆三路由 + landing）
- Delete: `frontend/src/views/Reconciliation.vue`
- Modify: `frontend/src/tests/views/Reconciliation.test.ts` → 拆分或删除
- Test: `frontend/src/tests/router/reconciliation.test.ts`（新建）

- [ ] **Step 1: 写失败测试**

测试三个路由可访问、`/reconciliation` 重定向到 `/reconciliation/orders`、旧 `Reconciliation.vue` 不再被引用。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/tests/router/reconciliation.test.ts`
Expected: FAIL

- [ ] **Step 3: 改路由**

`/reconciliation` redirect 到 `/reconciliation/orders`；加 `orders / differences / payment` 三路由，均 `permissionPage: 'reconciliation'`；`landingOptions` 把 `/reconciliation` 指向 `/reconciliation/orders`。删除 `Reconciliation.vue` 文件与对应测试。

- [ ] **Step 4: 运行测试确认通过 + 类型检查**

Run: `cd frontend && npx vitest run src/tests/router/reconciliation.test.ts && npm run build`
Expected: PASS + build 通过

- [ ] **Step 5: Commit**

```bash
git add frontend/src/router/index.ts frontend/src/tests/router/reconciliation.test.ts
git rm frontend/src/views/Reconciliation.vue frontend/src/tests/views/Reconciliation.test.ts
git commit -m "refactor(reconciliation): 拆单页为三子路由，移除旧 Reconciliation.vue"
```

---

## Task 10: 更新 update_issue 支持 conclusion_type + 全量回归

**Files:**
- Modify: `backend/apps/reconciliation/services.py:update_issue`（加 `conclusion_type` 参数）
- Modify: `backend/apps/reconciliation/views.py:ReconciliationIssueView.patch`（透传）
- Modify: `frontend/src/api/reconciliation.ts:updateReconciliationIssue`（加 conclusionType）
- Test: 补 `test_reconciliation_conclusion.py` 的 update 路径

- [ ] **Step 1: 写失败测试**

```python
def test_update_issue_conclusion_type(self, admin_user, branch, supplier):
    # patch conclusion_type='system_not_registered' 后读回一致
    ...
```

- [ ] **Step 2: 运行确认失败 → Step 3: 实现透传 → Step 4: 确认通过 → Step 5: 跑全量回归**

Run: `cd backend && pytest tests/ -k reconciliation -v && cd ../frontend && npm run build && npx vitest run`
Expected: 全绿

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(reconciliation): update_issue 支持结论类型；全量回归通过"
```

---

## Self-Review 结果

- **Spec 覆盖**：三页结构 ✓、分公司状态汇总 ✓、重新对账 ✓、固定结论类型 ✓、待付金额口径 ✓、归档门禁 ✓、全局任务上下文 ✓。
- **类型一致性**：`conclusion_type` / `build_branch_summary` / `rematch_task` / `build_payment_summary` / `useReconciliationTask` 在前后端命名对齐。
- **Review Focus 5 条**均已在对应 Task 的测试里钉住（金额口径 Task 4/8、rematch 幂等 Task 3、补录时机 Task 3、80 分公司性能 Task 2、归档门禁 Task 4/8）。
- **比例**：方案比 spec 略长，因含迁移与测试骨架，属合理。

---

**Plan complete and saved to `docs/superpowers/plans/2026-11-05-reconciliation-redesign.md`. Please review the plan. Which execution approach would you prefer?**

- **Subagent-driven** - 每个任务由新 subagent 实现 + 新 reviewer 审，最严，每任务/审各开新上下文，成本最高。
- **Native** - 我在本会话逐任务实现 + 末尾一次全分支 review，最快最省，适合任务间接口依赖紧密的场景。

**For this plan I recommend Subagent-driven**, because 10 个任务横跨后端迁移/接口/前端三页/路由整合，接口边界清晰可独立验收，且涉及金额计算与迁移等高风险点，每任务独立审能早一步拦住口径错误。Does the plan capture what you want, and which approach should we use?
