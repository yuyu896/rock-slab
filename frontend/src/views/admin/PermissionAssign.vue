<template>
  <div class="permission-assign">
    <header class="page-header">
      <h1>管理权限分配</h1>
      <p class="hint">
        职位（角色）仅用于组织归属，不再决定管理范围。在此为员工单独授予
        <strong>组织节点</strong>（全部数据 / 大区 / 分公司）与
        <strong>业务操作</strong> 权限。超级管理员自动拥有全部权限，无需分配。
      </p>
    </header>

    <section class="card">
      <label class="field">
        <span>选择员工</span>
        <el-select
          v-model="selectedUserId"
          filterable
          placeholder="按姓名 / 手机号搜索…"
          class="user-select"
          @change="loadUserGrants"
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
      </label>
    </section>

    <template v-if="selectedUser">
      <!-- 业务操作授权 -->
      <section class="card">
        <h2>业务操作</h2>
        <div class="op-grid">
          <label v-for="op in operations" :key="op.code" class="op-item">
            <input
              type="checkbox"
              :checked="hasOp(op.code)"
              :disabled="selectedUser.role === 'admin'"
              @change="onToggleOp(op.code, $event)"
            />
            <span>{{ op.label }}</span>
            <code class="op-code">{{ op.code }}</code>
          </label>
        </div>
      </section>

      <!-- 组织节点授权 -->
      <section class="card">
        <h2>组织节点（数据范围）</h2>
        <div class="scope-add">
          <select v-model="newScope.type" :disabled="newScope.type === 'all'">
            <option value="all">整个组织架构（全部数据）</option>
            <option value="region">大区</option>
            <option value="branch">分公司</option>
          </select>
          <select v-if="newScope.type !== 'all'" v-model="newScope.id">
            <option value="">请选择…</option>
            <option v-for="n in scopeOptions" :key="n.id" :value="n.id">{{ n.name }}</option>
          </select>
          <button class="btn-primary" :disabled="!canAddScope" @click="addScope">添加</button>
        </div>
        <p v-if="newScope.type === 'region' && newScope.id" class="region-hint">
          授予该大区即同时拥有其旗下 <strong>{{ regionBranchCount }}</strong> 个分公司的权限：
          {{ regionBranchNames }}
        </p>
        <p v-else-if="newScope.type === 'all'" class="region-hint">
          「全部数据」授权覆盖<strong>全部组织（含未来新增的大区 / 分公司 / 行政组）</strong>，每员工至多一条。
        </p>
        <ul class="scope-list">
          <li v-for="s in scopes" :key="s.id">
            <span v-html="scopeLabel(s)"></span>
            <button class="btn-link" @click="removeScope(s.id)">移除</button>
          </li>
          <li v-if="!scopes.length" class="empty">暂无组织节点授权（该员工仅可见自身相关数据）</li>
        </ul>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElSelect, ElOption } from 'element-plus'
import { getUsers } from '@/api/users'
import { getRegions } from '@/api/regions'
import { getBranches } from '@/api/branches'
import {
  createManagementScope, deleteManagementScope, getManagementScopes,
  createOperationGrant, deleteOperationGrant, getOperationGrants,
  getOperationCatalog,
  type ManagementScope, type OperationGrant, type OperationItem,
} from '@/api/permissions'
import { ROLE_LABELS } from '@/constants'
import type { User, Branch } from '@/types'

const users = ref<User[]>([])
const operations = ref<OperationItem[]>([])
const selectedUserId = ref('')
const scopes = ref<ManagementScope[]>([])
const grants = ref<OperationGrant[]>([])
const newScope = reactive<{ type: 'all' | 'region' | 'branch'; id: string }>({
  type: 'region', id: '',
})

const regions = ref<{ id: string; name: string }[]>([])
const branches = ref<Branch[]>([])

const selectedUser = computed(() => users.value.find(u => u.id === selectedUserId.value) || null)

const scopeOptions = computed(() => {
  if (newScope.type === 'region') return regions.value
  return branches.value
})

/** 当前选中大区旗下的分公司（用于"授大区即含分公司"提示） */
const regionBranches = computed(() =>
  newScope.type === 'region' && newScope.id
    ? branches.value.filter(b => b.region === newScope.id)
    : [],
)
const regionBranchCount = computed(() => regionBranches.value.length)
const regionBranchNames = computed(() =>
  regionBranches.value.map(b => b.name).join('、') || '（无）',
)

const canAddScope = computed(() => newScope.type === 'all' || !!newScope.id)

function roleLabel(role: string) {
  return ROLE_LABELS[role as keyof typeof ROLE_LABELS] || role
}

function hasOp(code: string) {
  return grants.value.some(g => g.code === code)
}

function onToggleOp(code: string, e: Event) {
  toggleOp(code, (e.target as HTMLInputElement).checked)
}

function branchesUnderRegion(regionId: string | null) {
  if (!regionId) return []
  return branches.value.filter(b => b.region === regionId)
}

function scopeLabel(s: ManagementScope) {
  const isAll = s.is_all_data ?? s.isAllData
  if (isAll) return '<strong>整个组织架构（全部数据）</strong>'
  if (s.region) {
    const r = regions.value.find(x => x.id === s.region)
    const cnt = branchesUnderRegion(s.region).length
    return `大区：<strong>${r?.name ?? '—'}</strong>（含 ${cnt} 个分公司）`
  }
  if (s.branch) {
    const b = branches.value.find(x => x.id === s.branch)
    return `分公司：${b?.name ?? '—'}`
  }
  if (s.team) {
    // 历史行政组授权（UI 已不再支持新建，但既有数据仍展示）
    return '行政组：（历史授权）'
  }
  return '—'
}

async function loadUserGrants() {
  if (!selectedUserId.value) {
    scopes.value = []
    grants.value = []
    return
  }
  const [s, g] = await Promise.all([
    getManagementScopes({ user: selectedUserId.value }),
    getOperationGrants({ user: selectedUserId.value }),
  ])
  scopes.value = Array.isArray(s.data) ? s.data : (s.data as any).results ?? []
  grants.value = Array.isArray(g.data) ? g.data : (g.data as any).results ?? []
}

async function toggleOp(code: string, checked: boolean) {
  if (!selectedUserId.value) return
  if (checked) {
    const { data } = await createOperationGrant({ user: selectedUserId.value, code })
    grants.value.push(data)
  } else {
    const g = grants.value.find(x => x.code === code)
    if (g) {
      await deleteOperationGrant(g.id)
      grants.value = grants.value.filter(x => x.id !== g.id)
    }
  }
}

async function addScope() {
  if (!selectedUserId.value) return
  if (newScope.type !== 'all' && !newScope.id) return
  const payload: Partial<ManagementScope> & { isAllData?: boolean } = { user: selectedUserId.value }
  if (newScope.type === 'all') {
    payload.isAllData = true
  } else if (newScope.type === 'region') {
    payload.region = newScope.id
  } else if (newScope.type === 'branch') {
    payload.branch = newScope.id
  } else {
    payload.team = newScope.id
  }
  try {
    const { data } = await createManagementScope(payload)
    scopes.value.push(data)
    newScope.id = ''
    newScope.type = 'region'
  } catch (e: any) {
    const detail = e?.response?.data?.detail || e?.response?.data?.[0] || '添加失败：该授权可能已存在或组合非法。'
    alert(typeof detail === 'string' ? detail : '添加失败：该授权可能已存在或组合非法。')
  }
}

async function removeScope(id: string) {
  await deleteManagementScope(id)
  scopes.value = scopes.value.filter(s => s.id !== id)
}

onMounted(async () => {
  const [u, op, r, b] = await Promise.all([
    getUsers(), getOperationCatalog(), getRegions(), getBranches(),
  ])
  users.value = u.data
  operations.value = op.data
  regions.value = r.data
  branches.value = b.data
})
</script>

<style scoped>
.permission-assign { padding: var(--space-6); max-width: 900px; margin: 0 auto; }
.page-header h1 { font-size: var(--text-2xl); font-weight: 700; color: var(--color-text-primary); }
.hint { color: var(--color-text-secondary); font-size: var(--text-sm); margin-top: var(--space-2); line-height: 1.6; }
.card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-5); margin-top: var(--space-4); }
.card h2 { font-size: var(--text-lg); font-weight: 600; margin-bottom: var(--space-3); color: var(--color-text-primary); }
.field { display: flex; flex-direction: column; gap: var(--space-1); }
.field span { font-size: var(--text-sm); color: var(--color-text-secondary); }
.user-select { width: 100%; }
.opt-phone { float: right; color: var(--color-text-tertiary); font-size: var(--text-xs); }
select { padding: var(--space-2) var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg-elevated); color: var(--color-text-primary); font-size: var(--text-sm); }
.op-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--space-3); }
.op-item { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); cursor: pointer; }
.op-code { margin-left: auto; font-size: var(--text-xs); color: var(--color-text-tertiary); }
.scope-add { display: flex; gap: var(--space-2); margin-bottom: var(--space-2); flex-wrap: wrap; }
.scope-add select { flex: 1; min-width: 140px; }
.region-hint { font-size: var(--text-sm); color: var(--color-text-secondary); margin: 0 0 var(--space-3); padding: var(--space-2) var(--space-3); background: var(--color-primary-50); border-radius: var(--radius-md); }
.scope-list { list-style: none; padding: 0; margin: 0; }
.scope-list li { display: flex; justify-content: space-between; align-items: center; padding: var(--space-2) 0; border-bottom: 1px solid var(--color-border-light); }
.scope-list .empty { color: var(--color-text-tertiary); justify-content: center; border: none; font-size: var(--text-sm); }
.btn-primary { padding: var(--space-2) var(--space-4); background: var(--color-primary-500); color: white; border: none; border-radius: var(--radius-md); cursor: pointer; font-size: var(--text-sm); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-link { background: none; border: none; color: var(--color-danger); cursor: pointer; font-size: var(--text-sm); }
</style>
