<template>
  <div class="permission-assign page-fill">
    <header class="page-header">
      <h1>权限分配</h1>
      <p class="hint">
        岗位定操作、任命定范围、特例才单独授予。三步完成一次任命；岗位模板仅预填勾选，
        运行时权限以授权表为准，超级管理员内置全部权限。
      </p>
    </header>

    <div class="assign-body">
      <!-- 左：三步 -->
      <div class="steps">
        <!-- ① 选人 -->
        <section class="card">
          <h2><span class="step-num">1</span>选择员工</h2>
          <el-select
            v-model="selectedUserId"
            filterable
            placeholder="按姓名 / 手机号搜索…"
            class="user-select"
            @change="onSelectUser"
          >
            <el-option
              v-for="u in users"
              :key="u.id"
              :value="u.id"
              :label="`${u.name}（${u.phone}）`"
            >
              <span>{{ u.name }}</span>
              <span class="opt-phone">{{ u.phone }} · {{ roleLabel(u.role) }}</span>
            </el-option>
          </el-select>
        </section>

        <template v-if="selectedUser">
          <!-- ② 岗位模板 -->
          <section class="card">
            <h2><span class="step-num">2</span>选择岗位（预填操作码，可增删）</h2>
            <div class="position-row">
              <label
                v-for="t in templates"
                :key="t.role"
                class="position-item"
                :class="{ active: selectedRole === t.role, disabled: t.role === 'admin' && selectedUser.role !== 'admin' }"
              >
                <input
                  type="radio"
                  :value="t.role"
                  :disabled="t.role === 'admin' && selectedUser.role !== 'admin'"
                  :checked="selectedRole === t.role"
                  @change="onPickRole(t.role)"
                />
                <span>{{ t.label }}</span>
                <span class="scope-hint">{{ scopeTypeLabel(t.scopeType) }}</span>
              </label>
            </div>
            <div class="op-grid">
              <label v-for="op in operations" :key="op.code" class="op-item">
                <input
                  type="checkbox"
                  :checked="draftOps.has(op.code)"
                  :disabled="isAdminUser"
                  @change="onToggleOp(op.code, $event)"
                />
                <span>{{ op.label }}</span>
                <code class="op-code">{{ op.code }}</code>
              </label>
            </div>
            <button class="btn-primary" :disabled="saving || !roleDirty" @click="saveRole">
              {{ saving ? '保存中…' : '保存岗位' }}
            </button>
          </section>

          <!-- ③ 任命节点 -->
          <section class="card">
            <h2><span class="step-num">3</span>任命节点（负责人 = 子树范围）</h2>
            <p class="step-desc">
              当前岗位建议任命：<strong>{{ scopeTypeLabel(activeTemplate?.scopeType) }}</strong>
              。任命保存后数据范围即时生效，卸任即回收。
            </p>
            <div class="appoint-row">
              <select v-model="appointType" class="appoint-select">
                <option value="region">大区负责人</option>
                <option value="team">行政组长</option>
                <option value="branch">分公司负责人</option>
              </select>
              <select v-model="appointNodeId" class="appoint-select">
                <option value="">请选择节点…</option>
                <option v-for="n in appointNodes" :key="n.id" :value="n.id">{{ n.label }}</option>
              </select>
              <button class="btn-primary" :disabled="saving || !appointNodeId" @click="saveAppointment">
                任命
              </button>
            </div>
            <ul class="appoint-list">
              <li v-for="a in appointments" :key="a.type + a.id">
                <span>{{ typeLabel(a.type) }}：<strong>{{ a.name }}</strong></span>
                <button class="btn-link" @click="removeAppointment(a)">卸任</button>
              </li>
              <li v-if="!appointments.length" class="empty">暂无任命（范围仅来自额外授权）</li>
            </ul>
          </section>

          <!-- 特例调整 -->
          <section class="card">
            <h2>特例调整（跨区兼管等）</h2>
            <div class="scope-add">
              <select v-model="newScope.type" :disabled="newScope.type === 'all'">
                <option value="all">整个组织架构（全部数据）</option>
                <option value="region">大区</option>
                <option value="branch">分公司</option>
                <option value="team">行政组</option>
              </select>
              <select v-if="newScope.type !== 'all'" v-model="newScope.id">
                <option value="">请选择…</option>
                <option v-for="n in scopeOptions" :key="n.id" :value="n.id">{{ n.name }}</option>
              </select>
              <button class="btn-primary" :disabled="!canAddScope" @click="addScope">添加授权</button>
            </div>
            <p v-if="newScope.type === 'region' && newScope.id" class="region-hint">
              授予该大区即同时拥有其旗下 <strong>{{ regionBranchCount }}</strong> 个分公司的权限。
            </p>
            <ul class="scope-list">
              <li v-for="s in scopes" :key="s.id">
                <span v-html="scopeLabel(s)"></span>
                <button class="btn-link" @click="removeScope(s.id)">移除</button>
              </li>
              <li v-if="!scopes.length" class="empty">暂无额外授权</li>
            </ul>
          </section>
        </template>
      </div>

      <!-- 右：实时权限预览 -->
      <aside v-if="selectedUser" class="preview">
        <h2>实时权限预览</h2>
        <div class="preview-block">
          <h3>当前生效</h3>
          <p class="preview-line">岗位：{{ roleLabel(selectedUser.role) }}</p>
          <p class="preview-line">范围：{{ effectiveRow ? scopeText(effectiveRow.scopeSummary) : '—' }}</p>
          <p class="preview-line">操作：{{ effectiveRow ? opsText(effectiveRow.operations) : '—' }}</p>
        </div>
        <div class="preview-block pending">
          <h3>若保存后</h3>
          <p class="preview-line">岗位：{{ roleLabel(selectedRole) }}</p>
          <p class="preview-line">
            范围：
            {{ previewScopeText }}
          </p>
          <p class="preview-line">操作：{{ isAdminUser ? '全部（内置）' : opsText([...draftOps]) }}</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getUsers, updateUser } from '@/api/users'
import { getRegions, updateRegion } from '@/api/regions'
import { getBranches, updateBranch } from '@/api/branches'
import { getTeams, updateTeam } from '@/api/teams'
import {
  createManagementScope, deleteManagementScope, getManagementScopes,
  createOperationGrant, deleteOperationGrant, getOperationGrants,
  getOperationCatalog, getPositionTemplates, getEffectivePermissions,
  type ManagementScope, type OperationGrant, type OperationItem,
  type PositionTemplate, type EffectivePermissionRow, type AppointmentItem,
} from '@/api/permissions'
import { ROLE_LABELS } from '@/constants'
import type { User, Branch, Region, Team } from '@/types'

const users = ref<User[]>([])
const operations = ref<OperationItem[]>([])
const templates = ref<PositionTemplate[]>([])
const selectedUserId = ref('')
const scopes = ref<ManagementScope[]>([])
const grants = ref<OperationGrant[]>([])
const effectiveRows = ref<EffectivePermissionRow[]>([])
const saving = ref(false)

const selectedRole = ref('')
const draftOps = ref<Set<string>>(new Set())

const appointType = ref<'region' | 'team' | 'branch'>('branch')
const appointNodeId = ref('')

const newScope = reactive<{ type: 'all' | 'region' | 'branch' | 'team'; id: string }>({
  type: 'region', id: '',
})

const regions = ref<Region[]>([])
const branches = ref<Branch[]>([])
const teams = ref<Team[]>([])

const selectedUser = computed(() => users.value.find(u => u.id === selectedUserId.value) || null)
const isAdminUser = computed(() => selectedUser.value?.role === 'admin')
const activeTemplate = computed(() => templates.value.find(t => t.role === selectedRole.value))
const effectiveRow = computed(() =>
  effectiveRows.value.find(r => r.user === selectedUserId.value) || null)
const appointments = computed<AppointmentItem[]>(() => effectiveRow.value?.appointments ?? [])

const appointNodes = computed(() => {
  if (appointType.value === 'region') {
    return regions.value.map(r => ({ id: r.id, label: r.name }))
  }
  if (appointType.value === 'team') {
    return teams.value.map(t => ({ id: t.id, label: `${t.name}（${regionName(t.region)}）` }))
  }
  return branches.value.map(b => ({ id: b.id, label: b.name }))
})

const scopeOptions = computed(() => {
  if (newScope.type === 'region') return regions.value
  if (newScope.type === 'team') return teams.value
  return branches.value
})
const canAddScope = computed(() => newScope.type === 'all' || !!newScope.id)
const regionBranchCount = computed(() =>
  newScope.type === 'region' && newScope.id
    ? branches.value.filter(b => b.region === newScope.id).length
    : 0,
)

const roleDirty = computed(() => selectedRole.value !== selectedUser.value?.role)

/** 若保存后的范围：当前生效范围 ∪ 待任命节点子树 */
const previewScopeText = computed(() => {
  const base = effectiveRow.value?.scopeSummary
  const parts: string[] = [base ? scopeText(base) : '—']
  if (appointNodeId.value) {
    const n = appointNodes.value.find(x => x.id === appointNodeId.value)
    if (n) parts.push(`+ 任命「${n.label}」子树`)
  }
  if (isAdminUser) return '全部（内置）'
  return parts.join(' ')
})

function roleLabel(role: string) {
  return ROLE_LABELS[role as keyof typeof ROLE_LABELS] || role
}
function scopeTypeLabel(t?: string) {
  if (t === 'all') return '全部数据'
  if (t === 'region') return '任命大区'
  if (t === 'team') return '任命行政组'
  if (t === 'branch') return '任命分公司'
  return '—'
}
function typeLabel(t: string) {
  return t === 'region' ? '大区负责人' : t === 'team' ? '行政组长' : '分公司负责人'
}
function scopeText(s: { all: boolean; branchCount: number | null }) {
  return s.all ? '全部' : `${s.branchCount ?? 0} 个分公司`
}
function opsText(ops: string[] | null) {
  if (ops === null) return '全部（内置）'
  if (!ops.length) return '（无）'
  return ops.map(c => operations.value.find(o => o.code === c)?.label || c).join('、')
}
function regionName(id: string) {
  return regions.value.find(r => r.id === id)?.name || ''
}

function onSelectUser() {
  const u = selectedUser.value
  selectedRole.value = u?.role || 'staff'
  draftOps.value = new Set(grants.value.map(g => g.code))
  const tpl = templates.value.find(t => t.role === selectedRole.value)
  if (tpl && tpl.scopeType !== 'all' && tpl.scopeType !== 'region') {
    appointType.value = tpl.scopeType as 'team' | 'branch'
  } else {
    appointType.value = 'branch'
  }
  appointNodeId.value = ''
}

function onPickRole(role: string) {
  selectedRole.value = role
  const tpl = templates.value.find(t => t.role === role)
  if (tpl && !tpl.allOperations && selectedUser.value?.role !== 'admin') {
    draftOps.value = new Set(tpl.operations)
  }
  if (tpl && tpl.scopeType !== 'all') {
    appointType.value = tpl.scopeType as 'region' | 'team' | 'branch'
  }
}

function onToggleOp(code: string, e: Event) {
  const checked = (e.target as HTMLInputElement).checked
  const next = new Set(draftOps.value)
  checked ? next.add(code) : next.delete(code)
  draftOps.value = next
}

async function refreshGrants() {
  if (!selectedUserId.value) {
    scopes.value = []
    grants.value = []
    effectiveRows.value = []
    return
  }
  const [s, g, e] = await Promise.all([
    getManagementScopes({ user: selectedUserId.value }),
    getOperationGrants({ user: selectedUserId.value }),
    getEffectivePermissions(),
  ])
  scopes.value = Array.isArray(s.data) ? s.data : (s.data as any).results ?? []
  grants.value = Array.isArray(g.data) ? g.data : (g.data as any).results ?? []
  effectiveRows.value = Array.isArray(e.data) ? e.data : []
}

async function saveRole() {
  if (!selectedUserId.value || !selectedRole.value) return
  saving.value = true
  try {
    // 岗位 + 操作码快照：岗位写用户，操作码对齐勾选集（增删差量）
    await updateUser(selectedUserId.value, { role: selectedRole.value } as any)
    const current = new Set(grants.value.map(g => g.code))
    for (const code of draftOps.value) {
      if (!current.has(code)) {
        const { data } = await createOperationGrant({ user: selectedUserId.value, code })
        grants.value.push(data)
      }
    }
    for (const g of grants.value) {
      if (!draftOps.value.has(g.code)) {
        await deleteOperationGrant(g.id)
      }
    }
    grants.value = grants.value.filter(g => draftOps.value.has(g.code))
    await reloadUser()
    ElMessage.success('岗位与操作码已保存')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function saveAppointment() {
  const nodeId = appointNodeId.value
  if (!nodeId) return
  saving.value = true
  try {
    if (appointType.value === 'region') {
      await updateRegion(nodeId, { manager: selectedUserId.value } as any)
    } else if (appointType.value === 'team') {
      await updateTeam(nodeId, { leader: selectedUserId.value } as any)
    } else {
      await updateBranch(nodeId, { manager: selectedUserId.value } as any)
    }
    appointNodeId.value = ''
    await refreshGrants()
    ElMessage.success('已任命，范围即时生效')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '任命失败')
  } finally {
    saving.value = false
  }
}

async function removeAppointment(a: AppointmentItem) {
  saving.value = true
  try {
    if (a.type === 'region') await updateRegion(a.id, { manager: null } as any)
    else if (a.type === 'team') await updateTeam(a.id, { leader: null } as any)
    else await updateBranch(a.id, { manager: null } as any)
    await refreshGrants()
    ElMessage.success('已卸任')
  } finally {
    saving.value = false
  }
}

async function addScope() {
  if (!selectedUserId.value) return
  if (newScope.type !== 'all' && !newScope.id) return
  const payload: Partial<ManagementScope> & { isAllData?: boolean } = { user: selectedUserId.value }
  if (newScope.type === 'all') payload.isAllData = true
  else if (newScope.type === 'region') payload.region = newScope.id
  else if (newScope.type === 'branch') payload.branch = newScope.id
  else payload.team = newScope.id
  try {
    const { data } = await createManagementScope(payload)
    scopes.value.push(data)
    newScope.id = ''
    newScope.type = 'region'
    await refreshGrants()
  } catch {
    ElMessage.error('添加失败：该授权可能已存在或组合非法。')
  }
}

async function removeScope(id: string) {
  await deleteManagementScope(id)
  scopes.value = scopes.value.filter(s => s.id !== id)
  await refreshGrants()
}

function branchesUnderRegion(regionId: string | null) {
  if (!regionId) return []
  return branches.value.filter(b => b.region === regionId)
}

function scopeLabel(s: ManagementScope) {
  const isAll = s.is_all_data ?? (s as any).isAllData
  if (isAll) return '<strong>整个组织架构（全部数据）</strong>'
  if (s.region) {
    const r = regions.value.find(x => x.id === s.region)
    const cnt = branchesUnderRegion(s.region).length
    return `大区：<strong>${r?.name ?? '—'}</strong>（含 ${cnt} 个分公司）`
  }
  if (s.branch) {
    const b = branches.value.find(x => x.id === s.branch)
    return `分公司：<strong>${b?.name ?? '—'}</strong>`
  }
  if (s.team) {
    const t = teams.value.find(x => x.id === s.team)
    return `行政组：<strong>${t?.name ?? '—'}</strong>`
  }
  return '—'
}

async function reloadUser() {
  const idx = users.value.findIndex(u => u.id === selectedUserId.value)
  if (idx >= 0 && selectedUser.value) {
    users.value[idx] = { ...users.value[idx], role: selectedRole.value as any }
  }
  await refreshGrants()
}

watch(selectedUserId, () => {
  void refreshGrants().then(() => onSelectUser())
})

onMounted(async () => {
  const [u, op, tpl, r, b, t] = await Promise.all([
    getUsers(), getOperationCatalog(), getPositionTemplates(),
    getRegions(), getBranches(), getTeams(),
  ])
  users.value = u.data
  operations.value = op.data
  templates.value = tpl.data
  regions.value = r.data
  branches.value = b.data
  teams.value = t.data
})
</script>

<style scoped>
.permission-assign { max-width: 1280px; width: 100%; margin: 0 auto; min-width: 0; overflow-y: auto; }
.page-header { margin-bottom: var(--space-4); flex-shrink: 0; }
.page-header h1 { font-size: var(--text-2xl); font-weight: 700; color: var(--color-text-primary); margin: 0; }
.hint { color: var(--color-text-secondary); font-size: var(--text-sm); margin-top: var(--space-2); line-height: 1.6; }
.assign-body { display: flex; gap: var(--space-5); align-items: flex-start; flex: 1; min-height: 0; }
.steps { flex: 1; min-width: 0; }
.card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-5); margin-bottom: var(--space-4); }
.card h2 { font-size: var(--text-lg); font-weight: 600; margin-bottom: var(--space-3); color: var(--color-text-primary); display: flex; align-items: center; gap: var(--space-2); }
.step-num { width: 22px; height: 22px; display: inline-flex; align-items: center; justify-content: center; background: var(--color-primary-500); color: #fff; border-radius: 50%; font-size: var(--text-xs); font-weight: 600; flex-shrink: 0; }
.step-desc { font-size: var(--text-sm); color: var(--color-text-secondary); margin: 0 0 var(--space-3); }
.user-select { width: 100%; }
.opt-phone { float: right; color: var(--color-text-tertiary); font-size: var(--text-xs); }
.position-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: var(--space-2); margin-bottom: var(--space-3); }
.position-item { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-md); cursor: pointer; font-size: var(--text-sm); }
.position-item.active { border-color: var(--color-primary-400); background: var(--color-primary-50); }
.position-item.disabled { opacity: 0.5; cursor: not-allowed; }
.scope-hint { margin-left: auto; font-size: var(--text-xs); color: var(--color-text-tertiary); }
.op-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: var(--space-2); margin-bottom: var(--space-3); }
.op-item { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); cursor: pointer; font-size: var(--text-sm); }
.op-code { margin-left: auto; font-size: var(--text-xs); color: var(--color-text-tertiary); }
.appoint-row, .scope-add { display: flex; gap: var(--space-2); margin-bottom: var(--space-3); flex-wrap: wrap; }
.appoint-select, .scope-add select { flex: 1; min-width: 160px; padding: var(--space-2) var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg-elevated); color: var(--color-text-primary); font-size: var(--text-sm); }
.appoint-list, .scope-list { list-style: none; padding: 0; margin: 0; }
.appoint-list li, .scope-list li { display: flex; justify-content: space-between; align-items: center; padding: var(--space-2) 0; border-bottom: 1px solid var(--color-border-light); font-size: var(--text-sm); }
.appoint-list li:last-child, .scope-list li:last-child { border-bottom: none; }
.empty { color: var(--color-text-tertiary); justify-content: center; border: none; }
.region-hint { font-size: var(--text-sm); color: var(--color-text-secondary); margin: 0 0 var(--space-3); padding: var(--space-2) var(--space-3); background: var(--color-primary-50); border-radius: var(--radius-md); }
.btn-primary { padding: var(--space-2) var(--space-4); background: var(--color-primary-500); color: #fff; border: none; border-radius: var(--radius-md); cursor: pointer; font-size: var(--text-sm); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-link { background: none; border: none; color: var(--color-danger); cursor: pointer; font-size: var(--text-sm); }
.preview { width: 340px; flex-shrink: 0; position: sticky; top: 0; background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-4); }
.preview h2 { font-size: var(--text-base); font-weight: 600; margin: 0 0 var(--space-3); }
.preview-block { padding: var(--space-3); border-radius: var(--radius-md); background: var(--color-bg-page); margin-bottom: var(--space-3); }
.preview-block.pending { border: 1px dashed var(--color-primary-300); background: var(--color-primary-50); }
.preview-block h3 { font-size: var(--text-sm); font-weight: 600; margin: 0 0 var(--space-2); color: var(--color-text-secondary); }
.preview-line { font-size: var(--text-sm); margin: 0 0 var(--space-1); line-height: 1.5; word-break: break-all; }
.preview-line:last-child { margin-bottom: 0; }
@media (max-width: 1024px) { .assign-body { flex-direction: column; } .preview { width: 100%; position: static; } }
</style>
