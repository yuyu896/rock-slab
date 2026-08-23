<template>
  <div class="permission-matrix page-fill">
    <header class="page-header">
      <h1>权限矩阵</h1>
      <p class="hint">
        上表：岗位模板预填的操作码（模板仅预填，实际权限以各人授权为准）。下表：全员生效权限
        ——任命定范围（负责人=子树）、岗位模板与特例授予定操作。
      </p>
    </header>

    <!-- 岗位 × 操作码 模板矩阵 -->
    <section class="card">
      <h2>岗位模板 × 操作码</h2>
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th class="col-op">操作码</th>
              <th v-for="t in templates" :key="t.role">{{ t.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="op in operations" :key="op.code">
              <td class="col-op">
                <div class="op-cell">
                  <span>{{ op.label }}</span>
                  <code class="op-code">{{ op.code }}</code>
                </div>
              </td>
              <td v-for="t in templates" :key="t.role" class="col-mark">
                <span v-if="t.allOperations || t.operations.includes(op.code)" class="mark">✔</span>
                <span v-else class="dim">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 用户生效权限卡 -->
    <section class="card">
      <h2>用户生效权限</h2>
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>姓名</th>
              <th>岗位</th>
              <th>任命节点</th>
              <th>额外授权</th>
              <th>生效范围</th>
              <th>持有操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.user">
              <td>
                <div class="name-cell">
                  <span>{{ row.name }}</span>
                  <span class="phone">{{ row.phone }}</span>
                </div>
              </td>
              <td>{{ roleLabel(row.role) }}</td>
              <td>{{ appointmentsText(row) }}</td>
              <td>{{ scopesText(row) }}</td>
              <td>{{ scopeText(row.scopeSummary) }}</td>
              <td class="col-ops">{{ opsText(row.operations) }}</td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="6" class="empty-cell">加载中…</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  getEffectivePermissions, getOperationCatalog, getPositionTemplates,
  type OperationItem, type PositionTemplate, type EffectivePermissionRow,
} from '@/api/permissions'
import { ROLE_LABELS } from '@/constants'

const operations = ref<OperationItem[]>([])
const templates = ref<PositionTemplate[]>([])
const rows = ref<EffectivePermissionRow[]>([])

function roleLabel(role: string) {
  return ROLE_LABELS[role as keyof typeof ROLE_LABELS] || role
}
function appointmentsText(row: EffectivePermissionRow) {
  if (!row.appointments.length) return '—'
  const label = (t: string) =>
    t === 'region' ? '大区' : t === 'team' ? '行政组' : '分公司'
  return row.appointments.map(a => `${label(a.type)}·${a.name}`).join('、')
}
function scopesText(row: EffectivePermissionRow) {
  if (!row.extraScopes.length) return '—'
  return row.extraScopes.map(s => {
    if (s.all) return '全部数据'
    if (s.region) return `大区授权`
    if (s.team) return `行政组授权`
    if (s.branch) return `分公司授权`
    return '—'
  }).join('、')
}
function scopeText(s: { all: boolean; branchCount: number | null }) {
  return s.all ? '全部' : `${s.branchCount ?? 0} 个分公司`
}
function opsText(ops: string[] | null) {
  if (ops === null) return '全部（内置）'
  if (!ops.length) return '—'
  return ops.map(c => operations.value.find(o => o.code === c)?.label || c).join('、')
}

onMounted(async () => {
  const [op, tpl, eff] = await Promise.all([
    getOperationCatalog(), getPositionTemplates(), getEffectivePermissions(),
  ])
  operations.value = op.data
  templates.value = tpl.data
  rows.value = eff.data
})
</script>

<style scoped>
.permission-matrix { max-width: 1400px; width: 100%; margin: 0 auto; min-width: 0; display: flex; flex-direction: column; }
.page-header { margin-bottom: var(--space-4); flex-shrink: 0; }
.page-header h1 { font-size: var(--text-2xl); font-weight: 700; color: var(--color-text-primary); margin: 0; }
.hint { color: var(--color-text-secondary); font-size: var(--text-sm); margin-top: var(--space-2); line-height: 1.6; }
.card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-5); margin-bottom: var(--space-4); display: flex; flex-direction: column; min-height: 0; }
.card h2 { font-size: var(--text-lg); font-weight: 600; margin-bottom: var(--space-3); color: var(--color-text-primary); flex-shrink: 0; }
.table-container { overflow: auto; flex: 1; min-height: 200px; background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); }
.data-table { width: 100%; border-collapse: collapse; }
.data-table thead th { position: sticky; top: 0; z-index: 1; }
.data-table th { background: var(--color-bg-elevated); padding: var(--space-3) var(--space-4); text-align: left; font-size: var(--text-sm); font-weight: 500; color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); white-space: nowrap; }
.data-table td { padding: var(--space-3) var(--space-4); font-size: var(--text-sm); color: var(--color-text-primary); border-bottom: 1px solid var(--color-border-light); vertical-align: middle; }
.data-table tbody tr:hover { background: var(--color-bg-elevated); }
.col-op { min-width: 220px; }
.op-cell { display: flex; align-items: center; gap: var(--space-2); }
.op-code { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.col-mark { text-align: center; }
.mark { color: var(--color-primary-600); font-weight: 600; }
.dim { color: var(--color-text-tertiary); }
.name-cell { display: flex; flex-direction: column; }
.phone { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.col-ops { max-width: 420px; }
.empty-cell { text-align: center; color: var(--color-text-tertiary); padding: var(--space-8) var(--space-4) !important; }
</style>
