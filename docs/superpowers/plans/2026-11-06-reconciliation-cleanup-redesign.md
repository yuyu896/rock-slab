# Reconciliation Redesign: Strip Conclusion Logic & Redesign Diff/Payment Pages

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the entire conclusion/note/status workflow from ReconciliationIssue, make the diff page read-only, and redesign the payment page as a branch master-detail table.

**Architecture:** Three independent tasks: (1) backend strips conclusion fields + migration, (2) frontend diff page becomes read-only list, (3) frontend payment page becomes branch master-detail. Task 2 and 3 both depend on Task 1's API shape, so Task 1 must land first; Tasks 2 and 3 can be implemented in either order after that.

**Tech Stack:** Python 3.13, Django 5.1, DRF, Vue 3.5 Composition API, TypeScript 5.7, Element Plus, Pinia

**Spec:** Design decisions recorded in session; see also `backend/apps/reconciliation/models.py`, `backend/apps/reconciliation/services.py`, `backend/apps/reconciliation/views.py` for current code.

## Global Constraints

- `trailing_slash=False`, `APPEND_SLASH=False` — no trailing slashes on URLs
- Django model fields use Chinese `verbose_name`; English class/method names
- `djangorestframework-camel-case` transforms snake_case → camelCase on all JSON responses
- Archive gate: zero non-matched comparisons (all result_types except `matched`)
- No new pip/npm dependencies
- PR #14 (`worktree-recon-followup-b`) must be closed on GitHub before this work begins — its M1/M2 changes are superseded by this plan
- Commit budget: one commit per task; commit message ends with `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`
- All changes local only; do not deploy or SSH to production

## Pre-flight: Close PR #14

Before Task 1, close PR #14 on GitHub (do not merge). Run:
```bash
gh pr close 14 --comment "Superseded by reconciliation redesign — M1/M2 absorbed into the cleanup plan."
```

## Review Focus

- Archive gate must block if ANY non-matched comparison exists (including `system_only`, `system_missing_serial`), not just billing diffs — the old gate only blocked on `order_row__isnull=False`.
- `pending_count` in version summary must equal raw non-matched count with no conclusion filter — tests that assert it changes after a PATCH to `/issues/<pk>` must be removed.
- `build_payment_summary` deduplicates billing amounts for `system_duplicate` (multiple comparisons sharing one `order_row`) — the `billed_order_rows` set must be preserved in the redesigned function.
- Removing `ReconciliationIssueHistory` via migration must handle rows that already exist in the DB (PostgreSQL CASCADE from the `issue` FK handles this automatically; verify the migration has no `atomic=False` needed — pure DDL).
- Frontend API type change from `ReconciliationPaymentSummary.rows` to `.branches[].rows` will break the payment page at compile time — both the API type and the component must be updated in the same Task 3 commit.

---

### Task 1: Backend — Strip Conclusion Logic + Migration

**Files:**
- Modify: `backend/apps/reconciliation/models.py`
- Modify: `backend/apps/reconciliation/services.py`
- Modify: `backend/apps/reconciliation/views.py`
- Modify: `backend/apps/reconciliation/urls.py`
- Create: `backend/apps/reconciliation/migrations/0005_remove_conclusion_fields.py`
- Modify: `backend/tests/test_reconciliation.py`

**Interfaces:**
- Produces (for Tasks 2 & 3): `build_payment_summary` returns `{'confirmed_amount', 'pending_amount', 'total_amount', 'can_archive', 'branches': [{'branch_id', 'branch_name', 'confirmed_amount', 'pending_amount', 'total_amount', 'diff_count', 'rows': [{'serial', 'internal_code', 'result_type', 'lease_start_date', 'accounting_date', 'billing_days', 'monthly_rent', 'month_amount'}]}]}`
- Produces: `build_branch_summary` returns list with `{'branch_id', 'branch_name', 'order_count', 'matched_count', 'diff_count', 'month_amount'}` — no `pending_count`
- Produces: `task_summary` / `build_version_summary` return `pending_count` = raw diff count (comparisons excluding matched)
- Produces: `GET /api/reconciliation/tasks/<pk>` response no longer has `unresolved_issues` key
- Produces: `GET /api/reconciliation/tasks` response `unresolved_summary` = `{'total_count': 0, 'groups': []}` (static empty)
- Produces: `PATCH /api/reconciliation/issues/<pk>` endpoint removed (returns 404)
- Produces: comparison payload `issue` object = `{'id', 'first_period', 'last_period'}` only

- [ ] **Step 1: Write failing test for new archive gate**

```python
# backend/tests/test_reconciliation.py — new test after existing archive tests
@pytest.mark.django_db
def test_archive_gate_blocks_any_non_matched_comparison(authenticated_client, admin_user, branch):
    supplier = Supplier.objects.create(name='归档门禁供应商')
    task = ReconciliationTask.objects.create(
        supplier=supplier, period=date(2026, 9, 1), created_by=admin_user,
    )
    version = ReconciliationUploadVersion.objects.create(
        task=task, version_number=1, file='reconciliation/gate.xlsx',
        uploaded_by=admin_user,
    )
    task.current_version = version
    task.save(update_fields=['current_version'])
    issue = ReconciliationIssue.objects.create(
        supplier=supplier, issue_key='gate-issue',
        issue_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        serial_normalized='GATE-SN', first_period=task.period, last_period=task.period,
    )
    ReconciliationComparison.objects.create(
        version=version, result_type=ReconciliationComparison.RESULT_SYSTEM_ONLY,
        issue=issue, system_serial_original='GATE-SN',
        system_branch_id=branch.pk, system_branch_name=branch.name,
    )
    resp = authenticated_client.post(f'/api/reconciliation/tasks/{task.pk}/archive')
    assert resp.status_code == 400
    assert '1 条差异' in resp.data['detail']
```

- [ ] **Step 2: Write failing test for pending_count = raw diff count**

```python
@pytest.mark.django_db
def test_pending_count_equals_diff_count_without_conclusion_filter(authenticated_client, admin_user):
    supplier = Supplier.objects.create(name='待处理无结论供应商')
    task = ReconciliationTask.objects.create(
        supplier=supplier, period=date(2026, 9, 1), created_by=admin_user,
    )
    version = ReconciliationUploadVersion.objects.create(
        task=task, version_number=1, file='reconciliation/pending-raw.xlsx',
        uploaded_by=admin_user, row_count=0, summary={},
    )
    task.current_version = version
    task.save(update_fields=['current_version'])
    issue = ReconciliationIssue.objects.create(
        supplier=supplier, issue_key='raw-pending-issue',
        issue_type=ReconciliationComparison.RESULT_ORDER_ONLY,
        serial_normalized='RAW-SN', first_period=task.period, last_period=task.period,
    )
    ReconciliationComparison.objects.create(
        version=version, result_type=ReconciliationComparison.RESULT_ORDER_ONLY, issue=issue,
    )
    response = authenticated_client.get('/api/reconciliation/tasks')
    assert response.status_code == 200
    assert response.data['results'][0]['pending_count'] == 1
```

- [ ] **Step 3: Run new tests to confirm they fail**

```bash
cd backend && pytest tests/test_reconciliation.py::test_archive_gate_blocks_any_non_matched_comparison tests/test_reconciliation.py::test_pending_count_equals_diff_count_without_conclusion_filter -v
```
Expected: FAIL

- [ ] **Step 4: Modify `backend/apps/reconciliation/models.py`**

Strip `ReconciliationIssue`:
- Remove class constants: `STATUS_OPEN`, `STATUS_NOT_RECURRED`, `STATUS_CLOSED`, `STATUS_CHOICES`, `CONCLUSION_CHOICES`
- Remove fields: `conclusion_type`, `conclusion`, `note`, `status`, `handled_by`, `handled_by_name`, `handled_at`, `closed_by`, `closed_by_name`, `closed_at`
- Replace `Meta.indexes` with empty list (or remove the `indexes` attribute): was `[models.Index(fields=['supplier', 'status', 'last_period'])]`

Delete `ReconciliationIssueHistory` class entirely (lines 162–177).

- [ ] **Step 5: Auto-generate the migration**

```bash
cd backend && python manage.py makemigrations reconciliation --name remove_conclusion_fields
```

Review the generated file in `backend/apps/reconciliation/migrations/0005_remove_conclusion_fields.py`. It must contain `RemoveField` operations for all 10 removed fields, a `RemoveIndex` for the supplier/status/last_period index, and `DeleteModel` for `ReconciliationIssueHistory`. No `atomic=False` needed (pure DDL). Correct manually if Django omitted any operation.

- [ ] **Step 6: Modify `backend/apps/reconciliation/services.py`**

**Imports:** remove `ReconciliationIssueHistory` from the model import list.

**`_issue_for()`:** simplify the `if not created:` branch to only update `last_period`:
```python
if not created:
    issue.last_period = max(issue.last_period, task.period)
    issue.save(update_fields=['last_period', 'updated_at'])
```
Remove `old_status`, `issue.status = ...`, and the `ReconciliationIssueHistory.objects.create()` call.

**`_prefetch_issues()`:** 
- Remove the `changed` list and `histories` list entirely
- Remove `old_status`, `issue.status = ...` assignments in the loop
- Only track `last_period` changes; still call `ReconciliationIssue.objects.bulk_update(changed, ['last_period', 'updated_at'], ...)` for period updates
- Remove `ReconciliationIssueHistory.objects.bulk_create(...)` call

**`build_comparison()`:** delete lines ~504–529 — the entire block that computes `previous_issues`, `recurring_issues`, and calls `bulk_update` on status + `bulk_create` on history.

**`update_issue()`:** delete the entire function (lines 638–669).

**`build_version_summary()`:** replace the `pending_count` query (currently filters on `issue__status` and `issue__conclusion_type`) with:
```python
pending_count = ReconciliationComparison.objects.filter(version=version).exclude(
    result_type=ReconciliationComparison.RESULT_MATCHED,
).count()
```

**`task_summary()`:** replace the inline `pending_count` re-computation (same pattern) with the same simplified query above.

**`build_payment_summary()`:** complete rewrite. New signature and return shape:

```python
def build_payment_summary(task, scope):
    # Returns:
    # {
    #   confirmed_amount, pending_amount, total_amount, can_archive,
    #   branches: [{branch_id, branch_name, confirmed_amount, pending_amount,
    #                total_amount, diff_count, rows: [{serial, internal_code,
    #                result_type, lease_start_date, accounting_date,
    #                billing_days, monthly_rent, month_amount}]}]
    # }
```

Logic:
- Query `version.comparisons.all()` through `_comparison_queryset_for_scope`, select_related `order_row__branch`
- Group by branch (order_row.branch takes priority; fall back to system_branch)
- Use `billed_order_rows` set (keyed by `order_row_id`) to deduplicate billing for `system_duplicate`
- Matched comparisons → `confirmed_amount`; non-matched with order_row → `pending_amount`
- `diff_count` per branch = non-matched comparison count (no deduplication needed for the count)
- `can_archive` = total non-matched comparisons == 0 (query: `comparisons.exclude(result_type='matched').count()`)

**`build_branch_summary()`:** remove `pending_count` from each bucket and from the return dict keys. Keep: `branch_id`, `branch_name`, `order_count`, `matched_count`, `diff_count`, `month_amount`.

- [ ] **Step 7: Modify `backend/apps/reconciliation/views.py`**

**Imports:** remove `ReconciliationIssueHistory`, `update_issue` from imports.

**`_comparison_payload()`:** simplify `issue` sub-dict to `{'id': str(issue.pk), 'first_period': issue.first_period.strftime('%Y-%m'), 'last_period': issue.last_period.strftime('%Y-%m')}` only.

**`_scoped_task_summary()`:** replace `pending_count` query (remove `issue__status` and `issue__conclusion_type` filters) with:
```python
pending_count = comparisons.exclude(
    result_type=ReconciliationComparison.RESULT_MATCHED,
).count()
```

**`ReconciliationTaskListView.get()`:**
- Simplify `pending_by_version` query: remove `.filter(issue__status__in=..., issue__conclusion_type='')` — keep only `.exclude(result_type=ReconciliationComparison.RESULT_MATCHED)`
- Replace `unresolved_groups` computation (currently queries `ReconciliationIssue.objects.filter(status__in=...)`) with static empty: `unresolved_summary = {'total_count': 0, 'groups': []}`

**`ReconciliationTaskDetailView.get()`:**
- Remove `unresolved_issues` block from payload (lines ~400–409)
- Simplify `result_filter == 'pending'` branch: remove `issue__status__in` and `issue__conclusion_type=''` filters; replace with just `.exclude(result_type=ReconciliationComparison.RESULT_MATCHED)`

**`ReconciliationTaskDetailView.post()` (archive):** replace `pending_count` gate with:
```python
diff_count = ReconciliationComparison.objects.filter(
    version_id=task.current_version_id,
).exclude(result_type=ReconciliationComparison.RESULT_MATCHED).count()
if diff_count > 0:
    from rest_framework.exceptions import ValidationError
    raise ValidationError({'detail': f'仍有 {diff_count} 条差异未处理'})
```

**`ReconciliationExportView.get()`:** in the main export, remove `issue.conclusion` and `issue.note` from `sheet.append(...)`. In `_export_payment()`, remove the `结论` column from headers and rows. Remove all references to `issue.conclusion` and `issue.note`.

**`ReconciliationIssueView` class:** delete entirely (both `patch` and `get` methods).

- [ ] **Step 8: Modify `backend/apps/reconciliation/urls.py`**

Remove `ReconciliationIssueView` from imports. Remove the line:
```python
path('issues/<uuid:pk>', ReconciliationIssueView.as_view()),
```

- [ ] **Step 9: Update tests in `backend/tests/test_reconciliation.py`**

**Delete** `test_task_list_pending_count_tracks_issue_conclusion_changes` (lines ~900–934) entirely.

**Update** `test_reconciliation_manage_requires_view_for_all_reads_and_writes` (around line 581): remove the `client.get(f'/api/reconciliation/issues/{visible_issue.pk}')` and `client.patch(f'/api/reconciliation/issues/{visible_issue.pk}', {'conclusion': ...})` assertion lines. Remove `visible_issue.conclusion == ''` assertion (line 668).

**Update** `test_reconciliation_reads_and_writes_require_supplier_view` (around line 676): remove `client.get(f'/api/reconciliation/issues/{issue.pk}')` and `client.patch(f'/api/reconciliation/issues/{issue.pk}', {'conclusion': '已核对'})` assertions.

**Update** `test_reconciliation_scope_blocks_cross_branch_issue_updates_and_task_archives` (around line 706): remove issue PATCH assertion (line ~765).

**Update** `test_task_list_unresolved_summary_groups_open_issues_and_excludes_closed` (line 393): this test creates `ReconciliationIssue` rows directly with a `status` field. After removing `status`, construction must omit `status=`. Also update the assertion — `unresolved_summary.total_count` will always be 0 now; either update the assertion or delete the test.

- [ ] **Step 10: Run all reconciliation tests**

```bash
cd backend && pytest tests/test_reconciliation.py -v --tb=short
```
Expected: all pass (or only failures in tests unrelated to conclusion logic).

- [ ] **Step 11: Apply migration to local DB**

```bash
cd backend && python manage.py migrate reconciliation
```
Expected: `0005_remove_conclusion_fields` applies cleanly. Run `python manage.py check_ledger_consistency` and confirm exit 0.

- [ ] **Step 12: Commit**

```bash
git add backend/apps/reconciliation/models.py \
        backend/apps/reconciliation/services.py \
        backend/apps/reconciliation/views.py \
        backend/apps/reconciliation/urls.py \
        backend/apps/reconciliation/migrations/0005_remove_conclusion_fields.py \
        backend/tests/test_reconciliation.py
git commit -m "feat(reconciliation): 移除结论逻辑——字段/历史表/endpoint 全部下线

删除 ReconciliationIssue 中的 conclusion_type/conclusion/note/status/handled*/closed* 字段
以及 ReconciliationIssueHistory 模型；废弃 update_issue() 和 PATCH /issues/<pk>；
归档门禁改为「零差异」；pending_count 改为直接统计非匹配行数。
迁移 0005 清理 DB。

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Frontend — Diff Page Redesign (Read-Only)

**Files:**
- Modify: `frontend/src/views/reconciliation/ReconciliationDifferences.vue`
- Modify: `frontend/src/api/reconciliation.ts`

**Interfaces:**
- Consumes from Task 1: `BranchSummaryItem` no longer has `pendingCount`; `ReconciliationComparison.issue` only has `id`, `firstPeriod`, `lastPeriod`
- Produces: no changes to composables or other pages

- [ ] **Step 1: Update `frontend/src/api/reconciliation.ts`**

Update `BranchSummaryItem` interface — remove `pendingCount`:
```typescript
export interface BranchSummaryItem {
  branchId: string
  branchName: string
  orderCount: number
  matchedCount: number
  diffCount: number
  monthAmount: string
}
```

Update `ReconciliationIssue` interface — keep only identity fields (no status/conclusion):
```typescript
export interface ReconciliationIssue {
  id: string
  firstPeriod: string
  lastPeriod: string
}
```

Remove `updateReconciliationIssue` export function.
Remove `getReconciliationIssueHistory` export function.

- [ ] **Step 2: Update `frontend/src/views/reconciliation/ReconciliationDifferences.vue` — script**

Remove from `<script setup>`:
- Import `updateReconciliationIssue` (remove from api import list)
- `noteEditing` ref
- `CONCLUSION_OPTIONS` constant
- `handleConclusionChange()`, `onConclusionChange()`, `handleNoteBlur()` functions
- `totalPendingCount` computed
- From KPI: remove `totalPendingCount` entirely

Update `branchStatusIcon()`:
```typescript
function branchStatusIcon(branch: BranchSummaryItem) {
  if (branch.diffCount > 0) return '🔴'
  return '✅'
}
```

- [ ] **Step 3: Update `ReconciliationDifferences.vue` — template**

Remove from `<template>`:
- The "待结论" KPI item (`<div class="kpi-item">` block with `kpi-pending`)
- From the detail expand table: the "结论" column (`<el-table-column label="结论" width="170">`) 
- From the detail expand table: the "备注" column (`<el-table-column label="备注" min-width="150">`)
- From the branch summary table: the "待结论" column (`<el-table-column label="待结论" width="80">`)

- [ ] **Step 4: Run type check**

```bash
cd frontend && npm run build 2>&1 | head -40
```
Expected: no TypeScript errors related to `conclusionType`, `pendingCount`, `updateReconciliationIssue`, `handleNoteBlur`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/reconciliation/ReconciliationDifferences.vue \
        frontend/src/api/reconciliation.ts
git commit -m "feat(reconciliation): 差异页改为只读视图，移除结论/备注交互

去掉结论下拉、备注输入和分公司「待结论」计数列；BranchSummaryItem
移除 pendingCount；ReconciliationIssue 接口仅保留 id/firstPeriod/lastPeriod。

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Frontend — Payment Page Master-Detail + API Update

**Files:**
- Modify: `frontend/src/api/reconciliation.ts`
- Modify: `frontend/src/views/reconciliation/ReconciliationPayment.vue`

**Interfaces:**
- Consumes from Task 1: `GET /api/reconciliation/tasks/<pk>/payment` returns `{confirmed_amount, pending_amount, total_amount, can_archive, branches: [{branch_id, branch_name, confirmed_amount, pending_amount, total_amount, diff_count, rows: [...]}]}`

- [ ] **Step 1: Update `frontend/src/api/reconciliation.ts` — payment types**

Replace `ReconciliationPaymentRow` and `ReconciliationPaymentSummary`:
```typescript
export interface ReconciliationPaymentRow {
  serial: string | null
  internalCode: string
  resultType: string
  leaseStartDate: string | null
  accountingDate: string | null
  billingDays: number | null
  monthlyRent: string | null
  monthAmount: string | null
}

export interface ReconciliationPaymentBranch {
  branchId: string
  branchName: string
  confirmedAmount: string
  pendingAmount: string
  totalAmount: string
  diffCount: number
  rows: ReconciliationPaymentRow[]
}

export interface ReconciliationPaymentSummary {
  confirmedAmount: string
  pendingAmount: string
  totalAmount: string
  canArchive: boolean
  branches: ReconciliationPaymentBranch[]
}
```

Add `ReconciliationPaymentBranch` to the file. Remove `exportPayment` if it references `conclusionType` (keep it but its server-side column is already cleaned up in Task 1).

- [ ] **Step 2: Run type check to expose all uses of old `rows` / `conclusionType`**

```bash
cd frontend && npm run build 2>&1 | grep -A2 "error TS"
```
This will list every place in ReconciliationPayment.vue that uses the old interface — use the output to guide the rewrite in Step 3.

- [ ] **Step 3: Rewrite `ReconciliationPayment.vue` — script**

Remove:
- `CONCLUSION_LABELS` constant and `conclusionLabel()` function
- `pendingRowCount` computed (replace below)

Add:
- `expandedBranches` ref: `ref(new Set<string>())` — tracks which branch rows are expanded
- `pendingRowCount` as: `computed(() => summary.value?.branches.reduce((s, b) => s + b.diffCount, 0) ?? 0)`

Keep: `loadSummary()`, `doExport()`, `doArchive()`, `formatMoney()`, `formatDate()`, `billingStatusLabel()`, `billingStatusType()`, `loading`, `archiving`, `exporting` — all unchanged.

- [ ] **Step 4: Rewrite `ReconciliationPayment.vue` — template**

Replace the `<!-- Detail table -->` section (the flat `el-table` over `summary?.rows`) with a master-detail table:

Master table rows = `summary?.branches ?? []`, columns:
- 分公司 (`branchName`)
- 已确认金额 (`confirmedAmount`, formatMoney)
- 待确认金额 (`pendingAmount`, formatMoney) — colored red if `> 0`
- 本月合计 (`totalAmount`, formatMoney)
- 差异数 (`diffCount`) — colored red if `> 0`

Each master row is expandable (type="expand"). The expand slot renders an inner `el-table` with `data="branch.rows"`, columns:
- 序列号 (`serial`)
- 内部编号 (`internalCode`)
- 差异类型 — `resultType` mapped via `resultTypeLabel()` helper:
  ```typescript
  function resultTypeLabel(t: string) {
    const m: Record<string, string> = {
      matched: '匹配', branch_mismatch: '分公司不一致',
      order_only: '仅订单有', system_only: '仅系统有',
      system_duplicate: '序列号重复', system_missing_serial: '缺少序列号',
    }
    return m[t] ?? t
  }
  ```
- 起租日期 (`leaseStartDate`, formatDate)
- 记账日期 (`accountingDate`, formatDate)
- 计费天数 (`billingDays`)
- 月租金 (`monthlyRent`, formatMoney)
- 本月金额 (`monthAmount`, formatMoney)

Remove the "结论" column from both master and detail. Remove `CONCLUSION_LABELS` usage.

- [ ] **Step 5: Run type check**

```bash
cd frontend && npm run build 2>&1 | head -40
```
Expected: clean build, no TS errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/reconciliation.ts \
        frontend/src/views/reconciliation/ReconciliationPayment.vue
git commit -m "feat(reconciliation): 待付金额页改为分公司主从表

ReconciliationPaymentSummary 从扁平行列表改为 branches[] 嵌套结构；
master 行显示分公司汇总，展开后展示明细行；移除结论列；
canArchive 语义改为零差异。

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
