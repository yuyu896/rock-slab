<template>
  <div class="permission-workspace page-fill">
    <header class="page-header">
      <div>
        <h1>权限分配</h1>
        <p class="hint">按账号设置数据范围和业务权限；员工权限按实际生效结果显示。</p>
      </div>
      <el-button :disabled="isDirty || loadingBaseline" :loading="loadingBaseline" @click="loadBaselinePreview">
        核对岗位权限基线
      </el-button>
    </header>

    <el-dialog
      v-model="baselineDialogVisible"
      title="岗位权限基线核对"
      width="min(1040px, calc(100vw - 32px))"
      top="5vh"
      :close-on-click-modal="false"
    >
      <div v-if="loadingBaseline" class="baseline-state">正在生成逐员工差异…</div>
      <template v-else-if="baselinePreview">
        <div class="baseline-summary">
          <div><span>当前版本</span><strong>{{ baselinePreview.from_version || '尚未初始化' }}</strong></div>
          <div><span>待确认版本</span><strong>{{ baselinePreview.to_version }}</strong></div>
          <div><span>在职普通员工</span><strong>{{ baselinePreview.active_employee_count }}</strong></div>
          <div><span>有差异员工</span><strong>{{ baselinePreview.changed_employee_count }}</strong></div>
        </div>
        <el-alert v-if="baselinePreview.has_changes" type="warning" :closable="false" show-icon>
          确认后将更新在职员工的岗位基线，保留个人追加和取消以及现有数据范围。停用员工重新启用时同步；未登记旧权限保留并列出核对。
        </el-alert>
        <el-alert v-else type="success" :closable="false" show-icon>
          当前已是最新岗位基线，无需更新。
        </el-alert>

        <section v-if="baselinePreview.role_changes.length" class="baseline-role-changes">
          <h3>岗位基线变化</h3>
          <div v-for="change in baselinePreview.role_changes" :key="change.role" class="baseline-role-row">
            <strong>{{ change.role_label }}</strong>
            <span v-if="change.added.length">新增：{{ change.added.map(item => item.label).join('、') }}</span>
            <span v-if="change.removed.length">取消：{{ change.removed.map(item => item.label).join('、') }}</span>
          </div>
        </section>

        <div class="baseline-table-scroll">
          <table class="baseline-table">
            <thead>
              <tr><th>员工</th><th>新增权限</th><th>取消权限</th><th>待核对旧权限</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in baselinePreview.employees" :key="row.user">
                <td>
                  <strong>{{ row.name }}</strong>
                  <small class="baseline-subtitle">{{ row.role_label }} · {{ row.branch_name || '未设置分公司' }}</small>
                </td>
                <td>{{ row.added.map(item => item.label).join('、') || '—' }}</td>
                <td>{{ row.removed.map(item => item.label).join('、') || '—' }}</td>
                <td>{{ row.legacy_codes.join('、') || '—' }}</td>
              </tr>
              <tr v-if="!baselinePreview.employees.length">
                <td colspan="4" class="baseline-empty">没有员工权限差异或待核对旧权限</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="baselinePreview.inactive_employee_count" class="baseline-note">
          {{ baselinePreview.inactive_employee_count }} 名停用员工不在本次同步范围内，重新启用时将同步岗位基线并保留个人调整和数据范围。
        </p>
        <p class="baseline-note">
          本次变更：新增 {{ baselinePreview.added_permission_count }} 项授权，取消 {{ baselinePreview.removed_permission_count }} 项授权；旧权限 {{ baselinePreview.legacy_permission_count }} 项保留待核对。
        </p>
      </template>
      <template #footer>
        <el-button @click="baselineDialogVisible = false">关闭</el-button>
        <el-button type="primary" :disabled="!baselinePreview?.has_changes || loadingBaseline" :loading="applyingBaseline" @click="confirmBaseline">
          确认应用基线
        </el-button>
      </template>
    </el-dialog>

    <div class="workspace-body">
      <aside class="people-panel" aria-label="员工列表">
        <div class="people-heading">
          <h2>员工</h2>
          <span>{{ filteredUsers.length }}</span>
        </div>
        <div class="people-tools">
          <el-input v-model="keyword" clearable placeholder="搜索姓名或手机号" aria-label="搜索员工" />
          <el-button
            class="filter-toggle"
            plain
            :aria-expanded="filterPanelOpen"
            aria-controls="employee-filter-panel"
            :aria-label="`${filterPanelOpen ? '收起' : '展开'}员工筛选，${activeFilterCount} 项已启用`"
            @click="filterPanelOpen = !filterPanelOpen"
          >
            <Filter aria-hidden="true" />
            <span>筛选</span>
            <span v-if="activeFilterCount" class="filter-count" aria-hidden="true">{{ activeFilterCount }}</span>
            <ArrowUp v-if="filterPanelOpen" aria-hidden="true" />
            <ArrowDown v-else aria-hidden="true" />
          </el-button>
        </div>
        <div v-show="filterPanelOpen" id="employee-filter-panel" class="people-filters" aria-label="员工筛选">
          <el-select v-model="filters.region" clearable filterable placeholder="全部大区" aria-label="按大区筛选" @change="onRegionChange">
            <el-option v-for="region in regions" :key="region.id" :label="region.name" :value="region.id" />
          </el-select>
          <el-select v-model="filters.branch" clearable filterable placeholder="全部分公司" aria-label="按分公司筛选">
            <el-option v-for="branch in visibleBranches" :key="branch.id" :label="branch.name" :value="branch.id" />
          </el-select>
          <el-select v-model="filters.role" clearable filterable placeholder="全部岗位" aria-label="按岗位筛选">
            <el-option v-for="role in roles" :key="role.code" :label="role.label" :value="role.code" />
          </el-select>
          <el-select v-model="filters.status" clearable placeholder="全部账号状态" aria-label="按账号状态筛选">
            <el-option label="在职" value="active" />
            <el-option label="已停用" value="inactive" />
          </el-select>
          <el-select v-model="filters.authorization" clearable placeholder="全部授权状态" aria-label="按授权状态筛选">
            <el-option label="有业务权限" value="granted" />
            <el-option label="无业务权限" value="none" />
          </el-select>
          <el-button class="filter-reset" text :disabled="activeFilterCount === 0" @click="resetPeopleFilters">重置筛选</el-button>
        </div>
        <div v-if="loadingUsers" class="people-state">正在加载员工…</div>
        <div v-else-if="!filteredUsers.length" class="people-state">没有匹配的员工</div>
        <div v-else class="people-list">
          <button
            v-for="user in filteredUsers"
            :key="user.id"
            type="button"
            class="person-row"
            :class="{ selected: selectedUserId === user.id }"
            :aria-current="selectedUserId === user.id ? 'true' : undefined"
            @click="selectUser(user.id)"
          >
            <span class="person-main">
              <span class="person-name">{{ user.name }}</span>
              <span class="person-branch">{{ branchLabel(user) }}</span>
            </span>
            <span v-if="selectedUserId === user.id && isDirty" class="unsaved-dot" title="有未保存更改" />
          </button>
        </div>
      </aside>

      <main class="editor-panel">
        <div v-if="loadingUsers || loadingAuthorization" class="editor-empty">正在读取授权信息…</div>
        <div v-else-if="!selectedUser" class="editor-empty">从左侧选择员工以查看或设置授权</div>
        <template v-else>
          <section class="employee-heading">
            <div>
              <div class="employee-title-row">
                <h2>{{ authorization?.user.name || selectedUser.name }}</h2>
                <span class="status-label" :class="{ inactive: authorization?.user.status !== 'active' && authorization?.user.status !== '正常' }">
                  {{ statusLabel(authorization?.user.status || selectedUser.status) }}
                </span>
                <span v-if="isSelectedAdmin" class="admin-label">系统管理员</span>
                <span class="authorization-label" :class="{ granted: hasBusinessAuthorization(selectedUser) }">
                  {{ authorizationLabel(selectedUser) }}
                </span>
              </div>
              <p class="employee-meta">
                {{ authorization?.user.phone || selectedUser.phone }}
                <span>·</span>{{ roleLabel(authorization?.user.role || selectedUser.role) }}
                <span>·</span>{{ employeeOrganization }}
              </p>
            </div>
            <span v-if="isDirty" class="draft-indicator">未保存</span>
            <span v-else class="saved-indicator">{{ isSelectedAdmin ? '系统内置权限' : '当前设置已保存' }}</span>
          </section>

          <section v-if="isSelectedAdmin" class="admin-summary" aria-live="polite">
            <strong>系统管理员自动拥有全部业务权限和全组织数据范围。</strong>
            <span>此账号的权限由系统内置，不能在此逐项修改。</span>
          </section>

          <section v-if="legacyOperations.length" class="legacy-warning" role="status">
            <strong>发现 {{ legacyOperations.length }} 项旧权限</strong>
            <span>旧权限默认保留。核对后可逐项选择撤销，撤销项会随本次保存一起生效。</span>
            <div class="legacy-list">
              <label v-for="item in legacyOperationDetails" :key="item.code" class="legacy-option">
                <input
                  type="checkbox"
                  :checked="legacyOperationsToRemove.includes(item.code)"
                  :disabled="saving"
                  @change="toggleLegacyOperation(item.code, $event)"
                />
                <span>
                  <strong>撤销 {{ item.label }}</strong>
                  <small v-if="item.description">{{ item.description }}</small>
                </span>
              </label>
            </div>
          </section>

          <section class="scope-section" aria-labelledby="scope-heading">
            <div class="section-heading">
              <div>
                <h3 id="scope-heading">数据范围</h3>
                <p>决定账号可以访问哪些组织数据，不会自动增加业务操作权限。</p>
              </div>
              <span class="current-summary">当前：{{ currentScopeText }}</span>
            </div>

            <div class="scope-modes" role="radiogroup" aria-label="数据范围模式">
              <label class="mode-option" :class="{ active: draftScopeMode === 'default' }">
                <input v-model="draftScopeMode" type="radio" value="default" :disabled="isSelectedAdmin" />
                <span><strong>跟随员工归属</strong><small>按员工所属组织确定</small></span>
              </label>
              <label class="mode-option" :class="{ active: draftScopeMode === 'custom' }">
                <input v-model="draftScopeMode" type="radio" value="custom" :disabled="isSelectedAdmin" />
                <span><strong>自定义组织范围</strong><small>选择一个或多个组织节点</small></span>
              </label>
              <label class="mode-option" :class="{ active: draftScopeMode === 'all' }">
                <input v-model="draftScopeMode" type="radio" value="all" :disabled="isSelectedAdmin" />
                <span><strong>全部组织</strong><small>仅扩大数据可见范围</small></span>
              </label>
            </div>

            <div v-if="draftScopeMode === 'custom' && !isSelectedAdmin" class="scope-picker">
              <el-tree-select
                v-model="draftScopeNodeKeys"
                :data="scopeTree"
                :props="scopeTreeProps"
                multiple
                filterable
                show-checkbox
                check-strictly
                default-expand-all
                node-key="key"
                collapse-tags
                collapse-tags-tooltip
                clearable
                placeholder="搜索并选择组织节点"
                aria-label="自定义组织范围"
              />
              <p v-if="!draftScopeNodeKeys.length" class="scope-warning">自定义范围至少选择一个组织节点。</p>
              <div v-else class="selected-nodes">
                <span v-for="key in draftScopeNodeKeys" :key="key" class="scope-chip">{{ nodeLabel(key) }}</span>
              </div>
            </div>
          </section>

          <section class="operations-section" aria-labelledby="operations-heading">
            <div class="section-heading">
              <div>
                <h3 id="operations-heading">业务权限</h3>
                <p>按页面模块配置具体操作；导出随对应查看权限开放。</p>
              </div>
              <span class="current-summary">{{ selectedModuleCount }} 个已授权模块 · {{ selectedOperationCount }} / {{ operations.length }} 项操作</span>
            </div>

            <div v-if="!operations.length" class="inline-state">暂无可配置的业务权限</div>
            <template v-else>
              <nav v-if="operationGroups.length > 1" class="module-quick-nav" aria-label="权限模块快速定位">
                <span class="module-quick-nav-label">定位模块</span>
                <button
                  v-for="module in operationGroups"
                  :key="module.code"
                  type="button"
                  class="module-quick-link"
                  @click="scrollToModule(module.code)"
                >
                  {{ module.label }}
                </button>
              </nav>
              <div class="module-list">
              <section
                v-for="module in operationGroups"
                :id="moduleSectionId(module.code)"
                :key="module.code"
                class="module-group"
              >
                <div class="module-heading">
                  <h4>{{ module.label }}</h4>
                  <span>{{ module.selectedCount }} / {{ module.operations.length }}</span>
                </div>
                <div class="operation-grid">
                  <label v-for="op in module.operations" :key="op.code" class="operation-option" :class="{ checked: hasOperation(op.code), disabled: isOperationDisabled(op) }">
                    <input
                      type="checkbox"
                      :checked="hasOperation(op.code)"
                      :disabled="isOperationDisabled(op)"
                      @change="toggleOperation(op.code, $event)"
                    />
                    <span class="operation-copy">
                      <strong>{{ op.label }}</strong>
                      <small v-if="op.description">{{ op.description }}</small>
                    </span>
                  </label>
                </div>
              </section>
              </div>
            </template>
          </section>

          <section v-if="isDirty && !isSelectedAdmin" class="changes-section" aria-live="polite">
            <div class="section-heading">
              <div>
                <h3>待保存变更</h3>
                <p>确认后将一次性保存数据范围与业务权限。</p>
              </div>
              <span class="change-count">{{ changeCount }} 项变更</span>
            </div>
            <div class="change-list">
              <div v-if="scopeDirty" class="change-row">
                <strong>数据范围</strong>
                <span>{{ currentScopeText }} <b>→</b> {{ draftScopeText }}</span>
              </div>
              <div v-for="op in addedOperations" :key="`add-${op.code}`" class="change-row added">
                <strong>新增权限</strong><span>{{ op.module_label }} · {{ op.label }}</span>
              </div>
              <div v-for="op in removedOperations" :key="`remove-${op.code}`" class="change-row removed">
                <strong>撤销权限</strong><span>{{ op.module_label }} · {{ op.label }}</span>
              </div>
              <div v-for="item in removedLegacyOperationDetails" :key="`remove-legacy-${item.code}`" class="change-row removed">
                <strong>撤销旧权限</strong><span>{{ item.label }}</span>
              </div>
            </div>
            <label class="reason-field">
              <span>变更原因 <small>选填</small></span>
              <el-input v-model="reason" type="textarea" :rows="2" maxlength="300" show-word-limit placeholder="可填写权限调整的背景或依据" />
            </label>
          </section>

          <footer v-if="!isSelectedAdmin" class="editor-actions">
            <span class="action-note">{{ isDirty ? '权限变更将在确认保存后生效' : '修改会先保留为草稿' }}</span>
            <div>
              <el-button :disabled="!isDirty || saving" @click="resetDraft">放弃更改</el-button>
              <el-button type="primary" :disabled="!isDirty || saving || invalidCustomScope" :loading="saving" @click="saveAuthorization">
                {{ saving ? '保存中' : '确认保存' }}
              </el-button>
            </div>
          </footer>
        </template>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onBeforeRouteLeave } from 'vue-router'
import { ArrowDown, ArrowUp, Filter } from '@element-plus/icons-vue'
import { getUsers } from '@/api/users'
import { getRegions } from '@/api/regions'
import { getBranches } from '@/api/branches'
import { getTeams } from '@/api/teams'
import {
  getOperationCatalog,
  getEffectivePermissions,
  getUserAuthorization,
  saveUserAuthorization as putUserAuthorization,
  getPositionBaselinePreview,
  applyPositionBaseline,
  type AuthorizationScopeMode,
  type EffectivePermissionRow,
  type PositionBaselinePreview,
  type PermissionOperation,
  type ScopeNode,
  type ScopeNodeType,
  type UserAuthorization,
} from '@/api/permissions'
import { ROLE_LABELS } from '@/constants'
import { handleApiError } from '@/utils/request'
import type { User, Region, Branch, Team } from '@/types'

type UserListItem = User & { region_name?: string; branch_name?: string }
type ScopeTreeOption = { key: string; label: string; children?: ScopeTreeOption[] }

const users = ref<UserListItem[]>([])
const effectivePermissions = ref<EffectivePermissionRow[]>([])
const operations = ref<PermissionOperation[]>([])
const regions = ref<Region[]>([])
const branches = ref<Branch[]>([])
const teams = ref<Team[]>([])
const authorization = ref<UserAuthorization | null>(null)
const selectedUserId = ref('')
const keyword = ref('')
const filters = reactive({ region: '', branch: '', role: '', status: '', authorization: '' })
const filterPanelOpen = ref(false)
const loadingUsers = ref(true)
const loadingAuthorization = ref(false)
const saving = ref(false)
const loadingBaseline = ref(false)
const applyingBaseline = ref(false)
const baselineDialogVisible = ref(false)
const baselinePreview = ref<PositionBaselinePreview | null>(null)
const draftOperations = ref<string[]>([])
const draftScopeMode = ref<AuthorizationScopeMode>('default')
const draftScopeNodeKeys = ref<string[]>([])
const legacyOperationsToRemove = ref<string[]>([])
const reason = ref('')

const selectedUser = computed(() => users.value.find(user => user.id === selectedUserId.value) || null)
const isSelectedAdmin = computed(() => authorization.value?.user.role === 'admin' || selectedUser.value?.role === 'admin')
const roles = computed(() => [...new Set(users.value.map(user => user.role))]
  .map(code => ({ code, label: roleLabel(code) })))
const visibleBranches = computed(() => branches.value.filter(branch => !filters.region || branch.region === filters.region))
const activeFilterCount = computed(() => Object.values(filters).filter(Boolean).length)
const permissionByUserId = computed(() => new Map(effectivePermissions.value.map(row => [row.user || row.id || '', row])))
const filteredUsers = computed(() => {
  const query = keyword.value.trim().toLocaleLowerCase()
  return users.value.filter(user => {
    const matchesKeyword = !query || `${user.name} ${user.phone}`.toLocaleLowerCase().includes(query)
    const branchId = user.branch || ''
    const branch = branches.value.find(item => item.id === branchId)
    const matchesRegion = !filters.region || branch?.region === filters.region
    const matchesBranch = !filters.branch || branchId === filters.branch
    const matchesRole = !filters.role || user.role === filters.role
    const matchesStatus = !filters.status || (isActive(user.status) ? 'active' : 'inactive') === filters.status
    const hasAuthorization = hasBusinessAuthorization(user)
    const matchesAuthorization = !filters.authorization
      || (filters.authorization === 'granted' ? hasAuthorization : !hasAuthorization)
    return matchesKeyword && matchesRegion && matchesBranch && matchesRole && matchesStatus && matchesAuthorization
  })
})

const availableScopeNodes = computed<ScopeNode[]>(() => [
  ...regions.value.map(region => ({ id: region.id, type: 'region' as const, name: region.name })),
  ...branches.value.map(branch => ({ id: branch.id, type: 'branch' as const, name: branch.name })),
  ...teams.value.map(team => ({ id: team.id, type: 'team' as const, name: team.name })),
])

const scopeTreeProps = { value: 'key', label: 'label', children: 'children' }
const scopeTree = computed<ScopeTreeOption[]>(() => regions.value.map(region => {
  const regionTeams = teams.value.filter(team => team.region === region.id)
  const teamIds = new Set(regionTeams.map(team => team.id))
  const teamOptions = regionTeams.map(team => ({
    key: `team:${team.id}`,
    label: team.name,
    children: branches.value
      .filter(branch => branch.team === team.id)
      .map(branch => ({ key: `branch:${branch.id}`, label: branch.name })),
  }))
  const ungroupedBranches = branches.value
    .filter(branch => branch.region === region.id && !teamIds.has(branch.team))
    .map(branch => ({ key: `branch:${branch.id}`, label: branch.name }))
  return {
    key: `region:${region.id}`,
    label: region.name,
    children: [...teamOptions, ...ungroupedBranches],
  }
}))

const nodeByKey = computed(() => new Map(availableScopeNodes.value.map(node => [scopeNodeKey(node), node])))
const organizationNames = computed(() => {
  const user = authorization.value?.user
  if (!user) return '—'
  return [user.region_name, user.branch_name].filter(Boolean).join(' / ') || '未设置'
})
const employeeOrganization = computed(() => organizationNames.value)

const operationModuleLabels: Record<string, string> = {
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

const inferredOperationModules: { module: string; matches: (code: string) => boolean }[] = [
  { module: 'workbench', matches: code => ['view_dashboard', 'view_notifications', 'view_all_notifications', 'view_approval_reports'].includes(code) },
  { module: 'dictionaries', matches: code => /_(categories|departments|suppliers|dictionary)$/.test(code) },
  { module: 'personnel', matches: code => /_(users|organizations)$/.test(code) },
  { module: 'asset_ledger', matches: code => code.includes('asset_ledger') || code === 'adjust_ledger' },
  { module: 'assets', matches: code => code === 'manage_assets' },
  { module: 'instances', matches: code => code.includes('instance') },
  { module: 'purchase', matches: code => code.includes('purchase') },
  { module: 'assignment', matches: code => code.includes('assignment') },
  { module: 'transfer', matches: code => code.includes('transfer') },
  { module: 'recovery', matches: code => code.includes('recovery') },
  { module: 'inventory', matches: code => code.includes('inventory') },
  { module: 'reports', matches: code => code === 'view_reports' || code.includes('reconciliation') },
  { module: 'audit', matches: code => code.includes('audit') },
  { module: 'permission_matrix', matches: code => code.includes('permission_matrix') },
]

function operationModule(operation: PermissionOperation) {
  const declaredModule = operation.module?.trim()
  if (declaredModule && operationModuleLabels[declaredModule]) return declaredModule
  const inferredModule = inferredOperationModules.find(({ matches }) => matches(operation.code))?.module
  return inferredModule || declaredModule || 'other'
}

const operationGroups = computed(() => {
  const grouped = new Map<string, { code: string; label: string; operations: PermissionOperation[] }>()
  for (const operation of operations.value) {
    const key = operationModule(operation)
    const declaredLabel = operation.module_label?.trim()
    const group = grouped.get(key) || {
      code: key,
      label: declaredLabel && declaredLabel !== '其他权限'
        ? declaredLabel
        : operationModuleLabels[key] || declaredLabel || '其他权限',
      operations: [],
    }
    group.operations.push(operation)
    grouped.set(key, group)
  }
  return [...grouped.values()].map(group => ({
    ...group,
    selectedCount: isSelectedAdmin.value
      ? group.operations.length
      : group.operations.filter(operation => draftOperations.value.includes(operation.code)).length,
  }))
})

function moduleSectionId(code: string) {
  return `permission-module-${code}`
}

function scrollToModule(code: string) {
  document.getElementById(moduleSectionId(code))?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const selectedOperationCount = computed(() => isSelectedAdmin.value
  ? operations.value.length
  : draftOperations.value.length)
const selectedModuleCount = computed(() => operationGroups.value.filter(group => group.selectedCount > 0).length)
const legacyOperations = computed(() => authorization.value?.legacy_operations || [])
const legacyOperationDetails = computed(() => {
  const details = authorization.value?.legacy_operation_details || []
  const byCode = new Map(details.map(item => [item.code, item.label]))
  return legacyOperations.value.map(code => ({
    code,
    label: byCode.get(code) || '未登记的旧权限',
    description: code === 'dispose_assets'
      ? '不再单独授权，直接处置按回收单权限处理；此旧授权不会自动转成回收单权限。审批回收单适用于重新入库和直接处置。'
      : code === 'manage_instances'
        ? '旧权限曾控制实例资料和图片维护，以及直接更换使用人和部门；不会自动变成新目录的查看、编辑、换人或打印权限。'
        : code === 'adjust_ledger'
          ? '旧权限用于手工创建台账调整单，历史台账导入流程也接受该权限；不会自动变成“导入资产台账”或“调整资产台账”，需逐账号核对。'
          : '',
  }))
})

const currentScopeText = computed(() => {
  const scope = authorization.value?.scope
  if (!scope) return '—'
  if (scope.mode === 'all') return '全部组织'
  if (scope.mode === 'default') return `跟随员工归属（${employeeOrganization.value}）`
  return scope.nodes.map(node => `${scopeTypeLabel(node.type)}：${node.name}`).join('、') || '无组织节点'
})

const draftScopeText = computed(() => {
  if (draftScopeMode.value === 'all') return '全部组织'
  if (draftScopeMode.value === 'default') return `跟随员工归属（${employeeOrganization.value}）`
  return draftScopeNodeKeys.value.map(nodeLabel).join('、') || '无组织节点'
})

const scopeDirty = computed(() => {
  const scope = authorization.value?.scope
  if (!scope || draftScopeMode.value !== scope.mode) return true
  if (draftScopeMode.value !== 'custom') return false
  const current = scope.nodes.map(scopeNodeKey).sort()
  const draft = [...draftScopeNodeKeys.value].sort()
  return current.length !== draft.length || current.some((key, index) => key !== draft[index])
})

const isDirty = computed(() => {
  if (!authorization.value || isSelectedAdmin.value) return false
  const current = [...authorization.value.operations].sort()
  const draft = [...draftOperations.value].sort()
  const operationDirty = current.length !== draft.length || current.some((code, index) => code !== draft[index])
  return scopeDirty.value || operationDirty || legacyOperationsToRemove.value.length > 0
})

const operationByCode = computed(() => new Map(operations.value.map(operation => [operation.code, operation])))
const addedOperations = computed(() => draftOperations.value
  .filter(code => !authorization.value?.operations.includes(code))
  .map(code => operationByCode.value.get(code))
  .filter((operation): operation is PermissionOperation => !!operation))
const removedOperations = computed(() => (authorization.value?.operations || [])
  .filter(code => !draftOperations.value.includes(code))
  .map(code => operationByCode.value.get(code))
  .filter((operation): operation is PermissionOperation => !!operation))
const removedLegacyOperationDetails = computed(() => legacyOperationDetails.value
  .filter(item => legacyOperationsToRemove.value.includes(item.code)))
const changeCount = computed(() => Number(scopeDirty.value) + addedOperations.value.length
  + removedOperations.value.length + removedLegacyOperationDetails.value.length)
const invalidCustomScope = computed(() => draftScopeMode.value === 'custom' && draftScopeNodeKeys.value.length === 0)

function roleLabel(role?: string) {
  if (!role) return '未设置岗位'
  return ROLE_LABELS[role as keyof typeof ROLE_LABELS] || role
}

function statusLabel(status?: string) {
  if (!status) return '状态未知'
  if (['active', '正常', '启用', 'enabled'].includes(status)) return '在职'
  if (['inactive', '禁用', '停用', 'disabled'].includes(status)) return '已停用'
  return status
}

function isActive(status?: string) {
  return ['active', '正常', '启用', 'enabled'].includes(status || '')
}

function hasBusinessAuthorization(user: UserListItem) {
  if (user.role === 'admin') return true
  const row = permissionByUserId.value.get(user.id)
  return !!row && !!(row.operations?.length || row.legacy_operations?.length)
}

function authorizationLabel(user: UserListItem) {
  if (user.role === 'admin') return '系统内置全权'
  return hasBusinessAuthorization(user) ? '已授予业务权限' : '未授予业务权限'
}

function branchLabel(user: UserListItem) {
  const name = user.branchName || user.branch_name
  if (name) return name
  return branches.value.find(branch => branch.id === user.branch)?.name || '未设置分公司'
}

function resetPeopleFilters() {
  filters.region = ''
  filters.branch = ''
  filters.role = ''
  filters.status = ''
  filters.authorization = ''
}

function onRegionChange() {
  if (filters.branch && !visibleBranches.value.some(branch => branch.id === filters.branch)) filters.branch = ''
}

function scopeNodeKey(node: ScopeNode) {
  return `${node.type}:${node.id}`
}

function scopeNodeLabel(node: ScopeNode) {
  const path = [node.name]
  if (node.type === 'team') {
    const team = teams.value.find(item => item.id === node.id)
    const region = regions.value.find(item => item.id === team?.region)
    if (region) path.unshift(region.name)
  } else if (node.type === 'branch') {
    const branch = branches.value.find(item => item.id === node.id)
    const team = teams.value.find(item => item.id === branch?.team)
    const region = regions.value.find(item => item.id === (team?.region || branch?.region))
    if (region) path.unshift(region.name)
    if (team) path.splice(path.length - 1, 0, team.name)
  }
  return `${scopeTypeLabel(node.type)} · ${path.join(' / ')}`
}

function scopeTypeLabel(type: ScopeNodeType) {
  return type === 'region' ? '大区' : type === 'branch' ? '分公司' : '行政组'
}

function nodeLabel(key: string) {
  const node = nodeByKey.value.get(key)
  if (node) return scopeNodeLabel(node)
  const [type, ...idParts] = key.split(':')
  const name = authorization.value?.scope.nodes.find(candidate => scopeNodeKey(candidate) === key)?.name
  const validType = type === 'region' || type === 'branch' || type === 'team' ? type : 'team'
  return `${scopeTypeLabel(validType)} · ${name || idParts.join(':')}`
}

function hasOperation(code: string) {
  return isSelectedAdmin.value || draftOperations.value.includes(code)
}

function isOperationDisabled(operation: PermissionOperation) {
  if (isSelectedAdmin.value) return true
  if (draftOperations.value.includes(operation.code)) return false
  return !(operation.prerequisites || []).every(code => draftOperations.value.includes(code))
}

function toggleOperation(code: string, event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  const next = new Set(draftOperations.value)
  const operation = operationByCode.value.get(code)
  if (checked) {
    if (operation && !(operation.prerequisites || []).every(prerequisite => next.has(prerequisite))) return
    next.add(code)
  } else {
    const removed = new Set([code])
    let changed = true
    while (changed) {
      changed = false
      for (const candidate of operations.value) {
        if (next.has(candidate.code) && (candidate.prerequisites || []).some(prerequisite => removed.has(prerequisite))) {
          removed.add(candidate.code)
          changed = true
        }
      }
    }
    removed.forEach(removedCode => next.delete(removedCode))
    const removedLabels = [...removed]
      .filter(removedCode => removedCode !== code)
      .map(removedCode => operationByCode.value.get(removedCode)?.label)
      .filter((label): label is string => !!label)
    if (removedLabels.length) {
      ElMessage.warning(`已取消“${operation?.label || code}”，并清除依赖权限：${removedLabels.join('、')}`)
    }
  }
  draftOperations.value = operations.value.map(operation => operation.code).filter(operationCode => next.has(operationCode))
}

function toggleLegacyOperation(code: string, event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  const next = new Set(legacyOperationsToRemove.value)
  if (checked) next.add(code)
  else next.delete(code)
  legacyOperationsToRemove.value = legacyOperations.value.filter(item => next.has(item))
}

function normalizeRows<T>(data: T[] | { results?: T[] }): T[] {
  return Array.isArray(data) ? data : data.results || []
}

function resetDraft() {
  if (!authorization.value) return
  draftOperations.value = [...authorization.value.operations]
  draftScopeMode.value = authorization.value.scope.mode
  draftScopeNodeKeys.value = authorization.value.scope.nodes.map(scopeNodeKey)
  legacyOperationsToRemove.value = []
  reason.value = ''
}

async function loadAuthorization(userId: string) {
  selectedUserId.value = userId
  authorization.value = null
  loadingAuthorization.value = true
  reason.value = ''
  try {
    const { data } = await getUserAuthorization(userId)
    if (selectedUserId.value !== userId) return
    authorization.value = data
    resetDraft()
  } catch (error) {
    if (selectedUserId.value === userId) ElMessage.error(handleApiError(error))
  } finally {
    if (selectedUserId.value === userId) loadingAuthorization.value = false
  }
}

async function selectUser(userId: string) {
  if (userId === selectedUserId.value || saving.value) return
  if (isDirty.value) {
    try {
      await ElMessageBox.confirm(
        '保存当前草稿后切换员工？选择“放弃更改”会丢弃当前草稿。',
        '有未保存更改',
        {
          confirmButtonText: '保存并切换',
          cancelButtonText: '放弃更改',
          distinguishCancelAndClose: true,
          type: 'warning',
        },
      )
      const saved = await saveAuthorization()
      if (saved) await loadAuthorization(userId)
    } catch (action) {
      if (action === 'cancel') await loadAuthorization(userId)
    }
    return
  }
  await loadAuthorization(userId)
}

async function saveAuthorization(): Promise<boolean> {
  if (!authorization.value || !selectedUserId.value || !isDirty.value || isSelectedAdmin.value) return false
  if (invalidCustomScope.value) {
    ElMessage.error('自定义范围至少选择一个组织节点')
    return false
  }
  if (draftScopeMode.value === 'custom' && draftScopeNodeKeys.value.some(key => !nodeByKey.value.has(key))) {
    ElMessage.error('组织节点已失效，请重新选择数据范围')
    return false
  }
  saving.value = true
  try {
    const scopeNodes = draftScopeMode.value === 'custom'
      ? draftScopeNodeKeys.value.map(key => nodeByKey.value.get(key)).filter((node): node is ScopeNode => !!node)
      : []
    await putUserAuthorization(selectedUserId.value, {
      operations: [...draftOperations.value],
      scope: { mode: draftScopeMode.value, nodes: scopeNodes },
      ...(legacyOperationsToRemove.value.length
        ? { remove_legacy_operations: [...legacyOperationsToRemove.value] }
        : {}),
      ...(reason.value.trim() ? { reason: reason.value.trim() } : {}),
    })
    const userId = selectedUserId.value
    const { data } = await getUserAuthorization(userId)
    if (selectedUserId.value === userId) {
      authorization.value = data
      resetDraft()
    }
    ElMessage.success('权限已保存')
    return true
  } catch (error) {
    ElMessage.error(handleApiError(error))
    return false
  } finally {
    saving.value = false
  }
}

async function loadBaselinePreview() {
  if (isDirty.value) {
    ElMessage.warning('请先保存或放弃当前员工的权限修改，再核对岗位基线')
    return
  }
  baselineDialogVisible.value = true
  loadingBaseline.value = true
  try {
    const { data } = await getPositionBaselinePreview()
    baselinePreview.value = data
  } catch (error) {
    baselineDialogVisible.value = false
    ElMessage.error(handleApiError(error))
  } finally {
    loadingBaseline.value = false
  }
}

async function confirmBaseline() {
  const preview = baselinePreview.value
  if (!preview?.has_changes || applyingBaseline.value) return
  try {
    await ElMessageBox.confirm(
      `将应用 ${preview.to_version} 基线，更新 ${preview.active_employee_count} 名在职普通员工；员工个人权限调整和数据范围会保留。`,
      '确认应用岗位权限基线',
      { confirmButtonText: '确认应用', cancelButtonText: '返回核对', type: 'warning' },
    )
  } catch {
    return
  }

  applyingBaseline.value = true
  try {
    const { data } = await applyPositionBaseline({
      expected_from_version: preview.from_version,
      preview_token: preview.preview_token,
    })
    const selectedId = selectedUserId.value
    const [nextPreview, permissionResponse, selectedAuthorization] = await Promise.all([
      getPositionBaselinePreview(),
      getEffectivePermissions(),
      selectedId ? getUserAuthorization(selectedId) : Promise.resolve(null),
    ])
    baselinePreview.value = nextPreview.data
    effectivePermissions.value = permissionResponse.data
    if (selectedId && selectedAuthorization && selectedUserId.value === selectedId) {
      authorization.value = selectedAuthorization.data
      resetDraft()
    }
    ElMessage.success(data.detail)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    applyingBaseline.value = false
  }
}

async function confirmLeaveWithDraft() {
  if (!isDirty.value || saving.value) return !saving.value
  try {
    await ElMessageBox.confirm(
      '保存当前权限草稿后离开？选择“放弃并离开”会丢弃未保存更改。',
      '有未保存更改',
      {
        confirmButtonText: '保存并离开',
        cancelButtonText: '放弃并离开',
        distinguishCancelAndClose: true,
        type: 'warning',
      },
    )
    return await saveAuthorization()
  } catch (action) {
    if (action === 'cancel') {
      resetDraft()
      return true
    }
    return false
  }
}

function protectBeforeUnload(event: BeforeUnloadEvent) {
  if (!isDirty.value) return
  event.preventDefault()
  event.returnValue = ''
}

onBeforeRouteLeave(() => confirmLeaveWithDraft())

onMounted(async () => {
  window.addEventListener('beforeunload', protectBeforeUnload)
  loadingUsers.value = true
  try {
    const [userResponse, operationResponse, permissionResponse, regionResponse, branchResponse, teamResponse] = await Promise.all([
      getUsers(), getOperationCatalog(), getEffectivePermissions(), getRegions(), getBranches(), getTeams(),
    ])
    users.value = normalizeRows(userResponse.data as UserListItem[] | { results?: UserListItem[] })
    operations.value = operationResponse.data
    effectivePermissions.value = permissionResponse.data
    regions.value = normalizeRows(regionResponse.data)
    branches.value = normalizeRows(branchResponse.data)
    teams.value = normalizeRows(teamResponse.data)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loadingUsers.value = false
  }
})

onUnmounted(() => window.removeEventListener('beforeunload', protectBeforeUnload))
</script>

<style scoped>
.permission-workspace { display: flex; flex-direction: column; min-width: 0; overflow: hidden; }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin: 0 auto var(--space-4); width: 100%; max-width: 1500px; flex-shrink: 0; }
.page-header h1 { margin: 0; color: var(--color-text-primary); font-size: var(--text-2xl); font-weight: 700; }
.hint { margin: var(--space-2) 0 0; color: var(--color-text-secondary); font-size: var(--text-sm); line-height: 1.5; }
.baseline-state { min-height: 120px; display: grid; place-items: center; color: var(--color-text-secondary); }
.baseline-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
.baseline-summary > div { display: flex; flex-direction: column; gap: 4px; padding: 10px 12px; border: 1px solid var(--color-border-light); border-radius: 6px; }
.baseline-summary span, .baseline-subtitle, .baseline-note { color: var(--color-text-secondary); font-size: var(--text-xs); }
.baseline-summary strong { font-size: var(--text-base); }
.baseline-role-changes { margin: 16px 0; }
.baseline-role-changes h3 { margin: 0 0 8px; font-size: var(--text-sm); }
.baseline-role-row { display: grid; grid-template-columns: 120px minmax(0, 1fr); gap: 8px; padding: 5px 0; font-size: var(--text-sm); }
.baseline-role-row span { min-width: 0; }
.baseline-subtitle { display: block; margin-top: 3px; }
.baseline-note { margin: 10px 0 0; line-height: 1.5; }
.baseline-table-scroll { max-height: 390px; overflow: auto; border: 1px solid var(--color-border-light); }
.baseline-table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: var(--text-sm); }
.baseline-table th, .baseline-table td { padding: 9px 10px; text-align: left; vertical-align: top; border-bottom: 1px solid var(--color-border-light); overflow-wrap: anywhere; }
.baseline-table th { position: sticky; top: 0; background: var(--color-bg-card); font-weight: 600; }
.baseline-table th:first-child { width: 18%; }
.baseline-table th:last-child { width: 20%; }
.baseline-empty { text-align: center !important; color: var(--color-text-secondary); }
.workspace-body { display: grid; grid-template-columns: minmax(250px, 290px) minmax(0, 1fr); gap: var(--space-4); width: 100%; max-width: 1500px; min-height: 0; flex: 1; margin: 0 auto; }
.people-panel, .editor-panel { min-width: 0; background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; }
.people-panel { display: flex; flex-direction: column; padding: var(--space-4); min-height: 0; }
.people-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
.people-heading h2 { margin: 0; font-size: var(--text-base); }
.people-heading > span { color: var(--color-text-tertiary); font-size: var(--text-sm); }
.people-tools { display: flex; align-items: center; gap: 8px; }
.people-tools :deep(.el-input) { min-width: 0; flex: 1; }
.filter-toggle { display: inline-flex; align-items: center; gap: 6px; flex: 0 0 auto; }
.filter-toggle :deep(svg) { width: 14px; height: 14px; }
.filter-count { display: inline-grid; min-width: 18px; height: 18px; padding: 0 4px; place-items: center; color: var(--color-primary-700); background: var(--color-primary-50); border-radius: 9px; font-size: var(--text-xs); line-height: 1; }
.people-filters { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--color-border-light); }
.people-filters :deep(.el-select) { width: 100%; min-width: 0; }
.filter-reset { grid-column: 1 / -1; justify-self: end; }
.people-list { overflow: auto; min-height: 0; margin: var(--space-3) calc(var(--space-2) * -1) 0; }
.person-row { width: 100%; display: flex; gap: 10px; align-items: center; text-align: left; padding: 9px; background: transparent; border: 0; border-left: 3px solid transparent; color: var(--color-text-primary); cursor: pointer; }
.person-row:hover { background: var(--color-bg-elevated); }
.person-row.selected { background: var(--color-primary-50); border-left-color: var(--color-primary-500); }
.person-main { display: grid; gap: 3px; min-width: 0; flex: 1; }
.person-name { font-size: var(--text-sm); font-weight: 600; }
.person-branch { overflow: hidden; color: var(--color-text-tertiary); font-size: var(--text-xs); text-overflow: ellipsis; white-space: nowrap; }
.unsaved-dot { width: 8px; height: 8px; margin-top: 4px; flex: 0 0 8px; background: var(--color-warning); border-radius: 50%; }
.people-state, .editor-empty { color: var(--color-text-tertiary); font-size: var(--text-sm); text-align: center; }
.people-state { padding: 28px 8px; }
.editor-panel { --editor-panel-padding: clamp(16px, 3vw, 28px); overflow-y: auto; padding: var(--editor-panel-padding); }
.editor-empty { display: grid; min-height: 260px; place-items: center; }
.employee-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; padding-bottom: 18px; border-bottom: 1px solid var(--color-border-light); }
.employee-title-row { display: flex; align-items: center; flex-wrap: wrap; gap: 9px; }
.employee-title-row h2 { margin: 0; font-size: var(--text-xl); }
.status-label, .admin-label { padding: 3px 7px; border-radius: 4px; background: var(--color-success-bg, #eaf7ef); color: var(--color-success, #16794b); font-size: var(--text-xs); }
.status-label.inactive { background: var(--color-bg-elevated); color: var(--color-text-secondary); }
.admin-label { background: var(--color-primary-50); color: var(--color-primary-700); }
.authorization-label { padding: 3px 7px; border-radius: 4px; background: var(--color-bg-elevated); color: var(--color-text-secondary); font-size: var(--text-xs); }
.authorization-label.granted { background: var(--color-primary-50); color: var(--color-primary-700); }
.employee-meta { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 0; color: var(--color-text-secondary); font-size: var(--text-sm); }
.draft-indicator { color: var(--color-warning); font-size: var(--text-sm); white-space: nowrap; }
.saved-indicator { color: var(--color-text-tertiary); font-size: var(--text-sm); white-space: nowrap; }
.admin-summary { display: grid; gap: 5px; padding: 13px 15px; margin-top: 18px; border-left: 3px solid var(--color-primary-500); background: var(--color-primary-50); font-size: var(--text-sm); }
.admin-summary span { color: var(--color-text-secondary); }
.legacy-warning { display: grid; gap: 7px; padding: 12px 14px; margin-top: 14px; border-left: 3px solid var(--color-warning); background: color-mix(in srgb, var(--color-warning) 9%, white); font-size: var(--text-sm); }
.legacy-warning > span { color: var(--color-text-secondary); line-height: 1.45; }
.legacy-list { display: grid; gap: 6px; }
.legacy-option { display: flex; align-items: flex-start; gap: 8px; padding: 8px 10px; background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 4px; cursor: pointer; }
.legacy-option input { margin-top: 3px; accent-color: var(--color-danger); }
.legacy-option span { display: grid; gap: 3px; min-width: 0; }
.legacy-option strong { color: var(--color-text-primary); font-size: var(--text-sm); font-weight: 500; }
.legacy-option small { color: var(--color-text-secondary); font-size: var(--text-xs); line-height: 1.4; }
.scope-section, .operations-section, .changes-section { padding: 22px 0; border-bottom: 1px solid var(--color-border-light); }
.section-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 14px; }
.section-heading h3 { margin: 0; color: var(--color-text-primary); font-size: var(--text-base); }
.section-heading p { margin: 5px 0 0; color: var(--color-text-secondary); font-size: var(--text-sm); line-height: 1.45; }
.current-summary { color: var(--color-text-secondary); font-size: var(--text-sm); text-align: right; }
.scope-modes { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; }
.mode-option { display: flex; align-items: flex-start; gap: 9px; min-height: 65px; padding: 11px; border: 1px solid var(--color-border); border-radius: 6px; cursor: pointer; }
.mode-option.active { border-color: var(--color-primary-500); background: var(--color-primary-50); }
.mode-option input { margin-top: 3px; accent-color: var(--color-primary-600); }
.mode-option span { display: grid; gap: 4px; }
.mode-option strong { font-size: var(--text-sm); }
.mode-option small { color: var(--color-text-tertiary); font-size: var(--text-xs); line-height: 1.4; }
.scope-picker { margin-top: 12px; }
.scope-picker :deep(.el-tree-select), .scope-picker :deep(.el-select) { width: 100%; }
.scope-warning { color: var(--color-warning); font-size: var(--text-sm); }
.selected-nodes { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 9px; }
.scope-chip { padding: 4px 8px; background: var(--color-bg-elevated); color: var(--color-text-secondary); font-size: var(--text-xs); border-radius: 4px; }
.module-list { display: grid; gap: 12px; }
.module-quick-nav { position: sticky; top: calc(0px - var(--editor-panel-padding) - 1px); z-index: 2; display: flex; align-items: center; gap: 6px; overflow-x: auto; margin: 0 0 12px; padding: 8px 0; background: var(--color-bg-card); scrollbar-width: thin; }
.module-quick-nav-label { flex: 0 0 auto; color: var(--color-text-tertiary); font-size: var(--text-xs); white-space: nowrap; }
.module-quick-link { flex: 0 0 auto; min-height: 32px; padding: 6px 10px; color: var(--color-text-secondary); background: var(--color-bg-elevated); border: 1px solid var(--color-border); border-radius: 4px; cursor: pointer; font-size: var(--text-xs); white-space: nowrap; }
.module-quick-link:hover, .module-quick-link:focus-visible { color: var(--color-primary-700); border-color: var(--color-primary-400); }
.module-group { scroll-margin-top: 60px; border: 1px solid var(--color-border-light); border-radius: 6px; overflow: hidden; }
.module-heading { display: flex; justify-content: space-between; align-items: center; padding: 10px 13px; background: var(--color-bg-elevated); }
.module-heading h4 { margin: 0; font-size: var(--text-sm); font-weight: 600; }
.module-heading span { color: var(--color-text-tertiary); font-size: var(--text-xs); }
.operation-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1px; background: var(--color-border-light); }
.operation-option { display: flex; align-items: flex-start; gap: 9px; min-width: 0; padding: 11px 13px; background: var(--color-bg-card); cursor: pointer; }
.operation-option.checked { background: color-mix(in srgb, var(--color-primary-50) 56%, white); }
.operation-option.disabled { cursor: default; }
.operation-option input { margin-top: 3px; accent-color: var(--color-primary-600); }
.operation-copy { display: grid; gap: 4px; min-width: 0; }
.operation-copy strong { font-size: var(--text-sm); font-weight: 500; }
.operation-copy small { color: var(--color-text-tertiary); font-size: var(--text-xs); line-height: 1.4; }
.inline-state { padding: 24px 0; color: var(--color-text-tertiary); font-size: var(--text-sm); }
.changes-section { border-bottom: 0; padding-bottom: 18px; }
.change-count { color: var(--color-primary-700); font-size: var(--text-sm); white-space: nowrap; }
.change-list { display: grid; border-top: 1px solid var(--color-border-light); }
.change-row { display: grid; grid-template-columns: 110px minmax(0, 1fr); gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--color-border-light); font-size: var(--text-sm); }
.change-row strong { color: var(--color-text-secondary); font-weight: 500; }
.change-row span { overflow-wrap: anywhere; }
.change-row b { padding: 0 5px; color: var(--color-text-tertiary); }
.change-row.added strong { color: var(--color-success, #16794b); }
.change-row.removed strong { color: var(--color-danger); }
.reason-field { display: grid; gap: 7px; margin-top: 15px; }
.reason-field > span { font-size: var(--text-sm); font-weight: 600; }
.reason-field small { margin-left: 5px; color: var(--color-text-tertiary); font-weight: 400; }
.editor-actions { position: sticky; bottom: calc(-1 * clamp(16px, 3vw, 28px)); display: flex; justify-content: space-between; align-items: center; gap: 16px; margin: 0 calc(-1 * clamp(16px, 3vw, 28px)); padding: 13px clamp(16px, 3vw, 28px); background: var(--color-bg-card); border-top: 1px solid var(--color-border); }
.action-note { color: var(--color-text-tertiary); font-size: var(--text-xs); }
.editor-actions > div { display: flex; gap: 8px; }
@media (max-width: 1000px) { .workspace-body { grid-template-columns: 230px minmax(0, 1fr); } .scope-modes { grid-template-columns: 1fr; } }
@media (max-width: 760px) {
  .permission-workspace { overflow: auto; }
  .page-header { align-items: flex-start; flex-direction: column; }
  .baseline-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .baseline-role-row { grid-template-columns: 1fr; gap: 2px; }
  .workspace-body { display: flex; flex-direction: column; }
  .people-panel { max-height: 330px; }
  .people-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .editor-panel { overflow: visible; }
  .module-quick-nav { top: 0; }
  .operation-grid { grid-template-columns: 1fr; }
  .section-heading { flex-direction: column; }
  .current-summary { text-align: left; }
  .editor-actions { align-items: flex-start; flex-direction: column; }
  .editor-actions > div { width: 100%; justify-content: flex-end; }
}
@media (max-width: 480px) {
  .people-list { grid-template-columns: 1fr; }
  .change-row { grid-template-columns: 1fr; gap: 4px; }
}
</style>
