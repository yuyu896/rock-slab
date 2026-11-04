<template>
  <div class="permission-matrix page-fill">
    <header class="page-header">
      <div>
        <h1>权限矩阵</h1>
        <p class="hint">查看全体员工当前生效的业务权限和数据范围。</p>
      </div>
    </header>

    <section class="filter-bar" aria-label="筛选实际权限">
      <el-input
        v-model="filters.keyword"
        clearable
        placeholder="搜索姓名或手机号"
        aria-label="搜索姓名或手机号"
        @keyup.enter="applyFilters"
        @clear="applyFilters"
      />
      <el-select v-model="filters.region" clearable filterable placeholder="全部大区" aria-label="按大区筛选" @change="onRegionChange">
        <el-option v-for="region in regions" :key="region.id" :label="region.name" :value="region.id" />
      </el-select>
      <el-select v-model="filters.branch" clearable filterable placeholder="全部分公司" aria-label="按分公司筛选" @change="applyFilters">
        <el-option v-for="branch in visibleBranches" :key="branch.id" :label="branch.name" :value="branch.id" />
      </el-select>
      <el-select v-model="filters.module" clearable filterable placeholder="全部模块" aria-label="按权限模块筛选" @change="onModuleChange">
        <el-option v-for="module in modules" :key="module.code" :label="module.label" :value="module.code" />
      </el-select>
      <el-select v-model="filters.operation" clearable filterable placeholder="全部操作" aria-label="按具体权限筛选" @change="applyFilters">
        <el-option v-for="operation in visibleOperations" :key="operation.code" :label="operationOptionLabel(operation)" :value="operation.code" />
      </el-select>
      <el-button type="primary" @click="applyFilters">筛选</el-button>
      <el-button @click="clearFilters">重置</el-button>
    </section>

    <div class="result-heading">
      <span>{{ rows.length }} 名员工</span>
      <span v-if="activeFilterText">筛选：{{ activeFilterText }}</span>
    </div>

    <section class="table-shell" aria-label="员工实际权限列表">
      <div v-if="loading" class="table-state">正在读取实际权限…</div>
      <div v-else-if="errorMessage" class="table-state error-state">{{ errorMessage }}</div>
      <div v-else-if="!rows.length" class="table-state">没有符合条件的员工</div>
      <div v-else class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>员工</th>
              <th>岗位</th>
              <th>所属组织</th>
              <th>数据范围</th>
              <th>实际业务权限</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.user || row.id || row.phone">
              <td class="employee-cell">
                <strong>{{ row.name }}</strong>
                <span>{{ row.phone }}</span>
              </td>
              <td>{{ roleLabel(row.role) }}</td>
              <td>{{ organizationText(row) }}</td>
              <td><span class="scope-summary">{{ scopeText(row) }}</span></td>
              <td class="permissions-cell">
                <template v-if="isAdmin(row)">
                  <span class="builtin-permission">全部业务权限</span>
                </template>
                <template v-else-if="!row.operations?.length">
                  <span class="no-permission">未授予业务权限</span>
                </template>
                <template v-else>
                  <div v-for="group in operationGroups(row)" :key="group.code" class="permission-line">
                    <strong>{{ group.label }}</strong>
                    <span>{{ group.labels.join('、') }}</span>
                  </div>
                  <span v-if="hasUnknownOperations(row)" class="unknown-permissions">
                    {{ unknownOperations(row).length }} 项权限不在当前目录
                  </span>
                </template>
                <span v-if="row.legacy_operations?.length" class="legacy-permissions">
                  {{ row.legacy_operations.length }} 项旧权限待迁移
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getEffectivePermissions,
  getOperationCatalog,
  getPermissionMatrixOrganizations,
  type EffectivePermissionFilters,
  type EffectivePermissionRow,
  type PermissionOperation,
  type PermissionMatrixOrganizationDirectory,
} from '@/api/permissions'
import { ROLE_LABELS } from '@/constants'
import { handleApiError } from '@/utils/request'

const rows = ref<EffectivePermissionRow[]>([])
const operations = ref<PermissionOperation[]>([])
const regions = ref<PermissionMatrixOrganizationDirectory['regions']>([])
const branches = ref<PermissionMatrixOrganizationDirectory['branches']>([])
const loading = ref(false)
const errorMessage = ref('')
const requestVersion = ref(0)
const filters = reactive({ keyword: '', region: '', branch: '', module: '', operation: '' })

const moduleLabels: Record<string, string> = {
  workbench: '工作台与通知',
  dictionaries: '基础资料',
  personnel: '员工与组织',
  asset_ledger: '资产台账',
  assets: '资产管理',
  instances: '实例档案',
  purchase: '采购入库',
  assignment: '领用出库',
  transfer: '调拨',
  recovery: '回收',
  inventory: '盘点',
  reports: '报表与对账',
  audit: '审计日志',
  permission_matrix: '权限矩阵',
}

function moduleLabel(operation: PermissionOperation) {
  const moduleCode = operation.module?.trim()
  if (moduleCode && moduleLabels[moduleCode]) return moduleLabels[moduleCode]

  const label = operation.module_label?.trim()
  if (label && !['undefined', 'null'].includes(label.toLowerCase())) return label
  return '其他权限'
}

function operationOptionLabel(operation: PermissionOperation) {
  const label = operation.label?.trim() || operation.code
  return `${moduleLabel(operation)} · ${label}`
}

const modules = computed(() => {
  const seen = new Map<string, string>()
  for (const operation of operations.value) {
    const code = operation.module?.trim() || 'other'
    if (!seen.has(code)) seen.set(code, moduleLabel(operation))
  }
  return [...seen.entries()].map(([code, label]) => ({ code, label }))
})
const visibleOperations = computed(() => operations.value.filter(operation => !filters.module || operation.module === filters.module))
const visibleBranches = computed(() => branches.value.filter(branch => !filters.region || branch.region === filters.region))
const activeFilterText = computed(() => {
  const parts = [
    filters.keyword.trim(),
    regions.value.find(region => region.id === filters.region)?.name,
    branches.value.find(branch => branch.id === filters.branch)?.name,
    modules.value.find(module => module.code === filters.module)?.label,
    operations.value.find(operation => operation.code === filters.operation)?.label,
  ].filter(Boolean)
  return parts.join(' / ')
})

function roleLabel(role: string) {
  return ROLE_LABELS[role as keyof typeof ROLE_LABELS] || role || '未设置'
}

function isAdmin(row: EffectivePermissionRow) {
  return row.role === 'admin' || row.operations === null
}

function organizationText(row: EffectivePermissionRow) {
  return [row.region_name, row.branch_name].filter(Boolean).join(' / ') || '未设置'
}

function scopeText(row: EffectivePermissionRow) {
  const scope = row.scope
  if (isAdmin(row) || scope?.mode === 'all' || row.scopeSummary?.all) return '全部组织'
  if (scope?.summary || row.scope_summary) return scope?.summary || row.scope_summary || ''
  if (scope?.mode === 'default') return `跟随员工归属（${organizationText(row)}）`
  if (scope?.mode === 'custom' && scope.nodes?.length) {
    return scope.nodes.map(node => `${node.name}`).join('、')
  }
  if (scope?.mode === 'custom') return '自定义范围：无组织节点'
  if (row.scopeSummary) return `${row.scopeSummary.branchCount ?? 0} 个分公司`
  return '跟随员工归属'
}

function operationGroups(row: EffectivePermissionRow) {
  const codes = isAdmin(row) ? operations.value.map(operation => operation.code) : row.operations || []
  const grouped = new Map<string, { code: string; label: string; labels: string[] }>()
  for (const code of codes) {
    const operation = operations.value.find(item => item.code === code)
    if (!operation) continue
    const moduleCode = operation.module?.trim() || 'other'
    const group = grouped.get(moduleCode) || { code: moduleCode, label: moduleLabel(operation), labels: [] }
    group.labels.push(operation.label?.trim() || operation.code)
    grouped.set(moduleCode, group)
  }
  return [...grouped.values()]
}

function unknownOperations(row: EffectivePermissionRow) {
  const known = new Set(operations.value.map(operation => operation.code))
  return (row.operations || []).filter(code => !known.has(code))
}

function hasUnknownOperations(row: EffectivePermissionRow) {
  return unknownOperations(row).length > 0
}

async function fetchRows(params: EffectivePermissionFilters = {}) {
  const version = ++requestVersion.value
  loading.value = true
  errorMessage.value = ''
  try {
    const { data } = await getEffectivePermissions(params)
    if (version === requestVersion.value) {
      rows.value = data
    }
  } catch (error) {
    if (version === requestVersion.value) {
      errorMessage.value = handleApiError(error)
      ElMessage.error(errorMessage.value)
    }
  } finally {
    if (version === requestVersion.value) loading.value = false
  }
}

function filterParams(): EffectivePermissionFilters {
  return {
    keyword: filters.keyword.trim() || undefined,
    region: filters.region || undefined,
    branch: filters.branch || undefined,
    module: filters.module || undefined,
    operation: filters.operation || undefined,
  }
}

function applyFilters() {
  void fetchRows(filterParams())
}

function onRegionChange() {
  if (filters.branch && !visibleBranches.value.some(branch => branch.id === filters.branch)) filters.branch = ''
  applyFilters()
}

function onModuleChange() {
  if (filters.operation && !visibleOperations.value.some(operation => operation.code === filters.operation)) filters.operation = ''
  applyFilters()
}

function clearFilters() {
  filters.keyword = ''
  filters.region = ''
  filters.branch = ''
  filters.module = ''
  filters.operation = ''
  applyFilters()
}

onMounted(async () => {
  const catalogLoad = getOperationCatalog()
    .then(({ data }) => { operations.value = data })
    .catch(error => { ElMessage.error(handleApiError(error)) })
  const organizationLoad = getPermissionMatrixOrganizations()
    .then(({ data }) => {
      regions.value = data.regions
      branches.value = data.branches
    })
    .catch(error => { ElMessage.error(handleApiError(error)) })
  await Promise.all([catalogLoad, organizationLoad, fetchRows()])
})
</script>

<style scoped>
.permission-matrix { display: flex; flex-direction: column; min-width: 0; overflow: hidden; }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; width: 100%; max-width: 1500px; margin: 0 auto var(--space-4); flex-shrink: 0; }
.page-header h1 { margin: 0; color: var(--color-text-primary); font-size: var(--text-2xl); font-weight: 700; }
.hint { margin: var(--space-2) 0 0; color: var(--color-text-secondary); font-size: var(--text-sm); line-height: 1.5; }
.filter-bar { display: grid; grid-template-columns: minmax(180px, 1.3fr) repeat(4, minmax(140px, 1fr)) auto auto; gap: 9px; width: 100%; max-width: 1500px; margin: 0 auto 12px; padding: 13px; background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; }
.filter-bar :deep(.el-select) { min-width: 0; }
.result-heading { display: flex; justify-content: space-between; gap: 14px; width: 100%; max-width: 1500px; margin: 0 auto 9px; color: var(--color-text-secondary); font-size: var(--text-sm); }
.table-shell { width: 100%; max-width: 1500px; min-height: 0; flex: 1; margin: 0 auto; overflow: hidden; background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; }
.table-scroll { height: 100%; overflow: auto; }
.table-state { display: grid; min-height: 220px; place-items: center; padding: 24px; color: var(--color-text-tertiary); font-size: var(--text-sm); }
.error-state { color: var(--color-danger); }
.data-table { width: 100%; min-width: 900px; border-collapse: collapse; }
.data-table thead th { position: sticky; top: 0; z-index: 1; background: var(--color-bg-table-header); }
.data-table th { padding: 12px 14px; text-align: left; color: var(--color-text-secondary); font-size: var(--text-sm); font-weight: 600; white-space: nowrap; border-bottom: 1px solid var(--color-border); }
.data-table td { padding: 12px 14px; vertical-align: top; color: var(--color-text-primary); font-size: var(--text-sm); border-bottom: 1px solid var(--color-border-light); }
.data-table tbody tr:hover { background: var(--color-bg-elevated); }
.employee-cell { display: grid; gap: 4px; min-width: 135px; }
.employee-cell strong { font-weight: 600; }
.employee-cell span { color: var(--color-text-tertiary); font-size: var(--text-xs); }
.scope-summary { display: inline-block; max-width: 260px; white-space: normal; line-height: 1.5; }
.permissions-cell { min-width: 320px; max-width: 680px; }
.permission-line { display: grid; grid-template-columns: 105px minmax(0, 1fr); gap: 8px; padding: 3px 0; line-height: 1.5; }
.permission-line strong { color: var(--color-text-secondary); font-weight: 500; }
.permission-line span { overflow-wrap: anywhere; }
.builtin-permission { display: inline-block; padding: 4px 8px; color: var(--color-primary-700); background: var(--color-primary-50); border-radius: 4px; }
.no-permission, .unknown-permissions { color: var(--color-text-tertiary); }
.unknown-permissions { display: block; margin-top: 4px; font-size: var(--text-xs); }
.legacy-permissions { display: block; margin-top: 5px; color: var(--color-warning); font-size: var(--text-xs); }
@media (max-width: 1050px) { .filter-bar { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 700px) {
  .permission-matrix { overflow: auto; }
  .page-header { align-items: flex-start; flex-direction: column; }
  .filter-bar { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .filter-bar :deep(.el-input) { grid-column: 1 / -1; }
  .result-heading { flex-direction: column; gap: 4px; }
  .table-shell { min-height: 50vh; }
}
@media (max-width: 420px) { .filter-bar { grid-template-columns: 1fr; } }
</style>
