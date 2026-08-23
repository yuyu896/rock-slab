<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getUsers, createUser, updateUser, deleteUser,
} from '@/api/users'
import { getRegions, createRegion, updateRegion, deleteRegion } from '@/api/regions'
import { getBranches, createBranch, updateBranch, deleteBranch } from '@/api/branches'
import { getTeams, createTeam, updateTeam, deleteTeam } from '@/api/teams'
import { getCompany, updateCompany } from '@/api/company'
import { handleApiError } from '@/utils/request'
import { usePermission } from '@/hooks/usePermission'
import { ROLE_LABELS } from '@/constants'
import type { User, Region, Branch, Team } from '@/types'
import { filterEmployeesByNode, sortEmployeesByRole, type NodeType } from '@/utils/orgTree'

const { canManageUsers, canManageOrganizations } = usePermission()

const regions = ref<Region[]>([])
const company = ref<{ id: string; name: string } | null>(null)
const branches = ref<Branch[]>([])
const teams = ref<Team[]>([])
const users = ref<User[]>([])
const loading = ref(false)

interface SelectedNode { type: NodeType; id: string; rawId: string; label: string }
const selectedNode = ref<SelectedNode | null>(null)
const expandedNodes = ref<Set<string>>(new Set(['group-root']))
const searchKeyword = ref('')

interface TreeNode {
  key: string
  type: NodeType
  label: string
  rawId: string
  children: TreeNode[]
}

const orgTree = computed<TreeNode[]>(() => {
  const regionNodes: TreeNode[] = regions.value.map(r => {
    const teamNodes: TreeNode[] = teams.value
      .filter(t => t.region === r.id)
      .map(t => ({
        key: `team-${t.id}`, type: 'team', label: t.name, rawId: t.id,
        children: branches.value
          .filter(b => b.team === t.id)
          .map(b => ({ key: `branch-${b.id}`, type: 'branch', label: b.name, rawId: b.id, children: [] })),
      }))
    return { key: `region-${r.id}`, type: 'region', label: `${r.name}（${r.code}）`, rawId: r.id, children: teamNodes }
  })
  return [{
    key: 'group-root', type: 'group', label: company.value?.name || '启航集团', rawId: '', children: regionNodes,
  }]
})

const nodeData = () => ({ users: users.value, branches: branches.value, regions: regions.value, teams: teams.value })

const employees = computed(() => {
  const kw = searchKeyword.value.trim().toLowerCase()
  const list = kw
    ? users.value.filter(u => u.name.toLowerCase().includes(kw) || (u.phone || '').includes(kw))
    : (selectedNode.value ? filterEmployeesByNode(selectedNode.value, nodeData()) : [])
  return sortEmployeesByRole(list)
})

function nodeCount(node: TreeNode): number {
  return filterEmployeesByNode(node, nodeData()).length
}

function selectNode(node: TreeNode) {
  searchKeyword.value = ''
  selectedNode.value = { type: node.type, id: node.key, rawId: node.rawId, label: node.label }
}
function toggleExpand(key: string) {
  const s = new Set(expandedNodes.value)
  s.has(key) ? s.delete(key) : s.add(key)
  expandedNodes.value = s
}

// ===== 弹窗（组织 / 员工 通用） =====
type EditType = 'region' | 'team' | 'branch' | 'user'
const showModal = ref(false)
const saving = ref(false)
const editingItem = ref<Record<string, any> | null>(null)
const editingEmployee = ref<Record<string, any> | null>(null)

// 选中节点对应的 region / team（用于新增下级时预填归属，均沿树派生）
const currentRegionId = computed(() => {
  const n = selectedNode.value
  if (!n) return ''
  if (n.type === 'region') return n.rawId
  if (n.type === 'team') return teams.value.find(t => t.id === n.rawId)?.region || ''
  if (n.type === 'branch') {
    const teamId = branches.value.find(b => b.id === n.rawId)?.team
    return teams.value.find(t => t.id === teamId)?.region || ''
  }
  return ''
})
const currentTeamId = computed(() => {
  const n = selectedNode.value
  if (!n) return ''
  if (n.type === 'team') return n.rawId
  if (n.type === 'branch') {
    return branches.value.find(b => b.id === n.rawId)?.team || ''
  }
  return ''
})

function addItem(type: EditType) {
  if (type === 'user') {
    // 员工走右侧编辑页（不弹窗，防误触）；组织归属只写分公司
    editingEmployee.value = {
      isNew: true, name: '', phone: '', role: 'staff',
      branch: selectedNode.value?.type === 'branch' ? selectedNode.value.rawId : '',
      status: 'active',
    }
    return
  }
  const base: Record<string, any> = { type, isNew: true, status: 'active' }
  if (type === 'team') base.region = currentRegionId.value
  if (type === 'branch') base.team = currentTeamId.value
  editingItem.value = base
  showModal.value = true
}

function editRegion(r: Region | undefined) { if (!r) return; editingItem.value = { type: 'region', isNew: false, id: r.id, name: r.name, code: r.code, manager: r.manager, status: r.status } ; showModal.value = true }
function editTeam(t: Team | undefined) { if (!t) return; editingItem.value = { type: 'team', isNew: false, id: t.id, name: t.name, region: t.region, leader: t.leader, status: t.status } ; showModal.value = true }
function editBranch(b: Branch | undefined) { if (!b) return; editingItem.value = { type: 'branch', isNew: false, id: b.id, name: b.name, code: b.code, team: b.team, address: b.address, phone: b.phone, manager: b.manager, status: b.status } ; showModal.value = true }
function editUser(u: User) {
  editingEmployee.value = { isNew: false, id: u.id, name: u.name, phone: u.phone, role: u.role, branch: u.branch || '', status: u.status }
}

// ===== 移动员工（区域 → 行政组 → 分公司 三级级联导航，仅写分公司） =====
const moveState = ref<{ employee: User; region: string; team: string; branch: string } | null>(null)
const moveTeamOptions = computed(() => {
  const r = moveState.value?.region
  return r ? teams.value.filter(t => t.region === r) : []
})
const moveBranchOptions = computed(() => {
  const s = moveState.value
  if (!s?.team) return []
  return branches.value.filter(b => b.team === s.team)
})
function regionOfBranch(branchId?: string): string {
  if (!branchId) return ''
  const teamId = branches.value.find(b => b.id === branchId)?.team
  return teams.value.find(t => t.id === teamId)?.region || ''
}
function startMove(emp: User) {
  moveState.value = { employee: emp, region: regionOfBranch(emp.branch), team: '', branch: '' }
}
// 切换区域/行政组时清空下级，避免提交到不匹配的目标
watch(() => moveState.value?.region, () => {
  if (moveState.value) { moveState.value.team = ''; moveState.value.branch = '' }
})
watch(() => moveState.value?.team, () => {
  if (moveState.value) moveState.value.branch = ''
})
async function confirmMove() {
  const s = moveState.value
  if (!s?.branch) { ElMessage.warning('请选择目标分公司'); return }
  const target = branches.value.find(b => b.id === s.branch)
  if (!target) return
  saving.value = true
  try {
    await updateUser(s.employee.id, { branch: target.id })
    ElMessage.success(`已将「${s.employee.name}」移动到「${target.name}」`)
    moveState.value = null
    await loadAll()
  } catch (e) {
    ElMessage.error(handleApiError(e))
  } finally {
    saving.value = false
  }
}

async function saveItem() {
  const item = editingItem.value
  if (!item) return
  saving.value = true
  try {
    if (item.type === 'region') {
      const payload = { name: item.name, code: item.code, manager: item.manager || null, status: item.status || 'active' }
      item.isNew ? await createRegion(payload) : await updateRegion(item.id, payload)
    } else if (item.type === 'team') {
      const payload = { name: item.name, region: item.region, leader: item.leader || null, status: item.status || 'active' }
      item.isNew ? await createTeam(payload) : await updateTeam(item.id, payload)
    } else if (item.type === 'branch') {
      if (!item.team) { ElMessage.warning('请选择所属行政组'); return }
      const payload = { name: item.name, code: item.code, team: item.team, address: item.address || '', phone: item.phone || '', manager: item.manager || null, status: item.status || 'active' }
      item.isNew ? await createBranch(payload) : await updateBranch(item.id, payload)
    }
    ElMessage.success(item.isNew ? '创建成功' : '保存成功')
    showModal.value = false
    editingItem.value = null
    await loadAll()
  } catch (e) {
    ElMessage.error(handleApiError(e))
  } finally {
    saving.value = false
  }
}

async function saveEmployee() {
  const e = editingEmployee.value
  if (!e) return
  saving.value = true
  try {
    const payload: Record<string, unknown> = {
      name: e.name, phone: e.phone, role: e.role,
      branch: e.branch || null, status: e.status || 'active',
    }
    if (e.isNew) {
      await createUser(payload as any)
    } else {
      await updateUser(e.id, payload as any)
    }
    ElMessage.success(e.isNew ? '创建成功' : '保存成功')
    editingEmployee.value = null
    await loadAll()
  } catch (err) {
    ElMessage.error(handleApiError(err))
  } finally {
    saving.value = false
  }
}

async function removeItem(item: Region | Team | Branch | User, type: EditType) {
  const label = (item as any).name || (item as any).phone
  try {
    await ElMessageBox.confirm(`确定删除「${label}」？`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    if (type === 'region') await deleteRegion(item.id)
    else if (type === 'team') await deleteTeam(item.id)
    else if (type === 'branch') await deleteBranch(item.id)
    else await deleteUser(item.id)
    ElMessage.success('已删除')
    await loadAll()
  } catch (e) {
    ElMessage.error(handleApiError(e))
  }
}

async function loadAll() {
  loading.value = true
  try {
    const [c, r, b, t, u] = await Promise.all([getCompany(), getRegions(), getBranches(), getTeams(), getUsers()])
    company.value = c.data
    regions.value = r.data
    branches.value = b.data
    teams.value = t.data
    users.value = u.data
  } catch (e) {
    ElMessage.error(handleApiError(e))
  } finally {
    loading.value = false
  }
}
onMounted(loadAll)

// ===== 编辑集团名 =====
const editingCompany = ref(false)
const companyNameDraft = ref('')
function startEditCompany() {
  companyNameDraft.value = company.value?.name || '启航集团'
  editingCompany.value = true
}
async function saveCompany() {
  const name = companyNameDraft.value.trim()
  if (!name) { ElMessage.warning('请输入集团名称'); return }
  saving.value = true
  try {
    await updateCompany({ name })
    ElMessage.success('集团名称已更新')
    editingCompany.value = false
    await loadAll()
  } catch (e) {
    ElMessage.error(handleApiError(e))
  } finally {
    saving.value = false
  }
}

function getBranchName(id?: string) { return id ? (branches.value.find(b => b.id === id)?.name || '-') : '-' }
function getTeamName(id?: string) { return id ? (teams.value.find(t => t.id === id)?.name || '-') : '-' }
function getRegionName(id?: string) { return id ? (regions.value.find(r => r.id === id)?.name || '-') : '-' }
</script>

<template>
  <div class="org-page">
    <!-- 左侧组织树 -->
    <aside class="org-tree">
      <div class="tree-header">
        <h2>组织架构</h2>
        <button class="refresh-btn" :disabled="loading" @click="loadAll">刷新</button>
      </div>
      <div class="tree-search">
        <input v-model="searchKeyword" placeholder="搜索员工姓名 / 手机号..." class="search-input" />
      </div>
      <div class="tree-body">
        <p v-if="!orgTree.length" class="tree-empty">暂无组织数据</p>
        <div v-for="group in orgTree" :key="group.key" class="tree-node">
          <div class="node-row" :class="{ selected: selectedNode?.id === group.key }" @click="selectNode(group); toggleExpand(group.key)">
            <span class="expand" :class="{ open: expandedNodes.has(group.key) }">▶</span>
            <span class="node-label group-label">{{ group.label }}</span>
            <span class="node-badge">{{ nodeCount(group) }}</span>
          </div>
          <div v-if="expandedNodes.has(group.key)" class="tree-children">
            <div v-for="region in group.children" :key="region.key" class="tree-node">
              <div class="node-row" :class="{ selected: selectedNode?.id === region.key }" @click="selectNode(region); toggleExpand(region.key)">
                <span class="expand" :class="{ open: expandedNodes.has(region.key) }">▶</span>
                <span class="node-label region-label">{{ region.label }}</span>
                <span class="node-badge">{{ nodeCount(region) }}</span>
              </div>
              <div v-if="expandedNodes.has(region.key)" class="tree-children">
                <div v-for="team in region.children" :key="team.key" class="tree-node">
                  <div class="node-row" :class="{ selected: selectedNode?.id === team.key }" @click="selectNode(team); toggleExpand(team.key)">
                    <span class="expand" :class="{ open: expandedNodes.has(team.key) }">▶</span>
                    <span class="node-label team-label">{{ team.label }}</span>
                    <span class="node-badge">{{ nodeCount(team) }}</span>
                  </div>
                  <div v-if="expandedNodes.has(team.key)" class="tree-children">
                    <div v-for="branch in team.children" :key="branch.key" class="tree-node">
                      <div class="node-row" :class="{ selected: selectedNode?.id === branch.key }" @click="selectNode(branch)">
                        <span class="expand placeholder"></span>
                        <span class="node-label branch-label">{{ branch.label }}</span>
                        <span class="node-badge">{{ nodeCount(branch) }}</span>
                      </div>
                    </div>
                    <p v-if="!team.children.length" class="no-child">（无分公司）</p>
                  </div>
                </div>
                <p v-if="!region.children.length" class="no-child">（无行政组）</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- 右侧主区 -->
    <main class="org-main">
      <!-- 员工编辑（右侧页面表单，防误触，不走弹窗） -->
      <div v-if="editingEmployee" class="employee-form-page">
        <div class="form-page-header">
          <button class="back-btn" @click="editingEmployee = null">← 返回列表</button>
          <h2>{{ editingEmployee.isNew ? '新增员工' : '编辑员工' }}</h2>
        </div>
        <div class="form-page-body">
          <div class="form-row"><label>姓名 <span class="req">*</span></label><input v-model="editingEmployee.name" class="form-input" placeholder="请输入姓名" /></div>
          <div class="form-row"><label>手机号（登录账号） <span class="req">*</span></label><input v-model="editingEmployee.phone" class="form-input" maxlength="11" placeholder="11 位手机号" /></div>
          <div class="form-row"><label>职务</label>
            <select v-model="editingEmployee.role" class="form-input">
              <option value="admin">系统管理员</option><option value="director">大区负责人</option><option value="manager">分公司负责人</option><option value="leader">行政组长</option><option value="staff">分公司行政</option>
            </select>
          </div>
          <div class="form-row"><label>所属分公司</label>
            <select v-model="editingEmployee.branch" class="form-input"><option value="">请选择</option><option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option></select>
          </div>
          <div class="form-row"><label>状态</label>
            <select v-model="editingEmployee.status" class="form-input"><option value="active">启用</option><option value="inactive">停用</option></select>
          </div>
          <div class="form-actions">
            <button class="action-btn" @click="editingEmployee = null">取消</button>
            <button class="action-btn primary" :disabled="saving" @click="saveEmployee">{{ saving ? '保存中…' : '保存' }}</button>
          </div>
        </div>
      </div>
      <template v-else>
      <!-- 顶部栏：标题 + 组织操作（按层级动态） -->
      <div class="main-header">
        <div class="header-title">
          <template v-if="searchKeyword">
            <h2>搜索“{{ searchKeyword }}”</h2>
            <span class="header-count">{{ employees.length }} 人</span>
          </template>
          <template v-else-if="selectedNode">
            <h2>{{ selectedNode.label }}</h2>
            <span class="header-count">{{ employees.length }} 人</span>
          </template>
          <template v-else>
            <h2>组织架构</h2>
            <span class="header-hint">从左侧选择节点查看员工</span>
          </template>
        </div>
        <div class="header-actions">
          <template v-if="!searchKeyword && selectedNode && canManageOrganizations">
            <!-- 集团根：编辑集团 + 新增区域 -->
            <button v-if="selectedNode.type === 'group'" class="action-btn" @click="startEditCompany">编辑集团</button>
            <button v-if="selectedNode.type === 'group'" class="action-btn primary" @click="addItem('region')">+ 区域</button>
            <!-- 区域：编辑区域 + 新增行政组 -->
            <button v-if="selectedNode.type === 'region'" class="action-btn" @click="editRegion(regions.find(r => r.id === selectedNode?.rawId))">编辑区域</button>
            <button v-if="selectedNode.type === 'region'" class="action-btn primary" @click="addItem('team')">+ 行政组</button>
            <!-- 行政组：编辑组 + 新增分公司 -->
            <button v-if="selectedNode.type === 'team' && selectedNode.rawId" class="action-btn" @click="editTeam(teams.find(t => t.id === selectedNode?.rawId))">编辑行政组</button>
            <button v-if="selectedNode.type === 'team' && selectedNode.rawId" class="action-btn primary" @click="addItem('branch')">+ 分公司</button>
            <!-- 分公司：编辑分公司 -->
            <button v-if="selectedNode.type === 'branch'" class="action-btn" @click="editBranch(branches.find(b => b.id === selectedNode?.rawId))">编辑分公司</button>
          </template>
        </div>
      </div>

      <!-- 员工操作栏 -->
      <div v-if="!searchKeyword && selectedNode && canManageUsers" class="employee-actions">
        <button class="action-btn primary" @click="addItem('user')">+ 创建员工</button>
        <span class="actions-hint">点击员工行可编辑</span>
      </div>

      <!-- 员工列表 -->
      <div v-if="selectedNode || searchKeyword" class="employee-section">
        <p v-if="!employees.length" class="empty">{{ searchKeyword ? '无匹配员工' : '该节点下暂无员工' }}</p>
        <table v-else class="employee-table">
          <thead>
            <tr>
              <th>姓名</th><th>职务</th><th>所属组织</th><th>账号</th><th>所属分公司</th><th v-if="canManageUsers">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="emp in employees" :key="emp.id">
              <td class="clickable" @click="editUser(emp)">{{ emp.name }}</td>
              <td>{{ ROLE_LABELS[emp.role] || emp.role }}</td>
              <td>{{ getTeamName(branches.find(b => b.id === emp.branch)?.team) }}</td>
              <td>{{ emp.phone }}</td>
              <td>{{ getBranchName(emp.branch) }}</td>
              <td v-if="canManageUsers">
                <button class="row-btn" @click="editUser(emp)">编辑</button>
                <button class="row-btn" @click="startMove(emp)">移动</button>
                <button class="row-btn danger" @click="removeItem(emp, 'user')">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-main">
        <p>请从左侧选择组织节点</p>
      </div>
      </template>
    </main>

    <!-- 通用弹窗：新增/编辑 组织/员工 -->
    <div v-if="editingItem" class="modal-mask" @click.self="editingItem = null">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingItem.isNew ? '新增' : '编辑' }}{{ editingItem.type === 'region' ? '区域' : editingItem.type === 'team' ? '行政组' : editingItem.type === 'branch' ? '分公司' : '员工' }}</h3>
          <button class="modal-close" @click="editingItem = null">×</button>
        </div>
        <div class="modal-body">
          <!-- 通用：名称 -->
          <div class="form-row">
            <label>{{ editingItem.type === 'user' ? '姓名' : '名称' }} <span class="req">*</span></label>
            <input v-model="editingItem.name" class="form-input" placeholder="请输入" />
          </div>
          <!-- 区域 / 分公司：编码 -->
          <div v-if="editingItem.type === 'region'" class="form-row">
            <label>区域编码 <span class="req">*</span></label>
            <input v-model="editingItem.code" class="form-input" placeholder="如 HUADONG" />
          </div>
          <div v-if="editingItem.type === 'branch'" class="form-row">
            <label>分公司编码 <span class="req">*</span></label>
            <input v-model="editingItem.code" class="form-input" placeholder="如 SH001（2-4位字母+3位数字）" />
          </div>
          <!-- 员工：手机号 / 角色 -->
          <div v-if="editingItem.type === 'user'" class="form-row">
            <label>手机号（登录账号） <span class="req">*</span></label>
            <input v-model="editingItem.phone" class="form-input" placeholder="11 位手机号" maxlength="11" />
          </div>
          <div v-if="editingItem.type === 'user'" class="form-row">
            <label>职务 <span class="req">*</span></label>
            <select v-model="editingItem.role" class="form-input">
              <option value="admin">超级管理员</option>
              <option value="director">行政总监</option>
              <option value="manager">行政经理</option>
              <option value="supervisor">行政主管</option>
              <option value="leader">行政组长</option>
              <option value="staff">行政专员</option>
            </select>
          </div>
          <!-- 员工：分公司（唯一组织归属，区域/行政组沿树派生） -->
          <div v-if="editingItem.type === 'user'" class="form-row">
            <label>所属分公司</label>
            <select v-model="editingItem.branch" class="form-input">
              <option value="">请选择</option>
              <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
            </select>
          </div>
          <!-- 分公司：所属行政组（唯一父级，必填） -->
          <div v-if="editingItem.type === 'branch'" class="form-row">
            <label>所属行政组 <span class="req">*</span></label>
            <select v-model="editingItem.team" class="form-input">
              <option value="">请选择</option>
              <optgroup v-for="r in regions" :key="r.id" :label="r.name">
                <option v-for="t in teams.filter(x => x.region === r.id)" :key="t.id" :value="t.id">{{ t.name }}</option>
              </optgroup>
            </select>
          </div>
          <!-- 分公司：地址 / 电话 -->
          <div v-if="editingItem.type === 'branch'" class="form-row">
            <label>地址</label>
            <input v-model="editingItem.address" class="form-input" />
          </div>
          <div v-if="editingItem.type === 'branch'" class="form-row">
            <label>联系电话</label>
            <input v-model="editingItem.phone" class="form-input" />
          </div>
          <!-- 状态 -->
          <div class="form-row">
            <label>状态</label>
            <select v-model="editingItem.status" class="form-input">
              <option value="active">启用</option>
              <option value="inactive">停用</option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button class="action-btn" :disabled="saving" @click="showModal = false">取消</button>
          <button class="action-btn primary" :disabled="saving" @click="saveItem">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>

    <!-- 移动员工弹窗 -->
    <div v-if="moveState" class="modal-mask" @click.self="moveState = null">
      <div class="modal">
        <div class="modal-header">
          <h3>移动员工</h3>
          <button class="modal-close" @click="moveState = null">×</button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <label>员工</label>
            <div class="move-employee-name">{{ moveState.employee.name }}（{{ moveState.employee.phone }}）</div>
          </div>
          <div class="form-row">
            <label>目标区域 <span class="req">*</span></label>
            <select v-model="moveState.region" class="form-input">
              <option value="">请选择</option>
              <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
            </select>
          </div>
          <div class="form-row">
            <label>目标行政组 <span class="req">*</span></label>
            <select v-model="moveState.team" class="form-input">
              <option value="">请选择</option>
              <option v-for="t in moveTeamOptions" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
          </div>
          <div class="form-row">
            <label>目标分公司 <span class="req">*</span></label>
            <select v-model="moveState.branch" class="form-input">
              <option value="">请选择</option>
              <option v-for="b in moveBranchOptions" :key="b.id" :value="b.id">{{ b.name }}</option>
            </select>
          </div>
          <p v-if="moveState?.branch" class="move-team-hint">
            将归属行政组：<strong>{{ getTeamName(branches.find(b => b.id === moveState?.branch)?.team) }}</strong>
          </p>
        </div>
        <div class="modal-footer">
          <button class="action-btn" :disabled="saving" @click="moveState = null">取消</button>
          <button class="action-btn primary" :disabled="saving" @click="confirmMove">{{ saving ? '移动中…' : '确认移动' }}</button>
        </div>
      </div>
    </div>

    <!-- 编辑集团弹窗 -->
    <div v-if="editingCompany" class="modal-mask" @click.self="editingCompany = false">
      <div class="modal">
        <div class="modal-header">
          <h3>编辑集团</h3>
          <button class="modal-close" @click="editingCompany = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <label>集团名称 <span class="req">*</span></label>
            <input v-model="companyNameDraft" class="form-input" placeholder="请输入集团名称" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="action-btn" :disabled="saving" @click="editingCompany = false">取消</button>
          <button class="action-btn primary" :disabled="saving" @click="saveCompany">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.org-page { display: flex; height: 100%; gap: 1px; background: var(--color-border-light); }
.org-tree { width: 320px; background: var(--color-bg-card); display: flex; flex-direction: column; overflow: hidden; }
.tree-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid var(--color-border-light); }
.tree-header h2 { margin: 0; font-size: 1.1rem; }
.refresh-btn { border: 1px solid var(--color-border); background: transparent; border-radius: 6px; padding: 4px 10px; cursor: pointer; color: var(--color-text-secondary); }
.refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.tree-search { padding: 8px 12px; border-bottom: 1px solid var(--color-border-light); }
.search-input { width: 100%; height: 32px; padding: 0 10px; border: 1px solid var(--color-border); border-radius: 6px; font-size: 0.85rem; outline: none; background: var(--color-bg-page); box-sizing: border-box; }
.search-input:focus { border-color: var(--color-primary-400); }
.tree-body { flex: 1; overflow-y: auto; padding: 8px; }
.tree-empty, .no-child { color: var(--color-text-tertiary); font-size: 0.85rem; padding: 8px; }
.tree-node { user-select: none; }
.node-row { display: flex; align-items: center; gap: 6px; padding: 6px 8px; border-radius: 6px; cursor: pointer; }
.node-row:hover { background: var(--color-primary-50); }
.node-row.selected { background: var(--color-primary-100); }
.expand { font-size: 0.7rem; color: var(--color-text-tertiary); transition: transform 0.15s; width: 12px; text-align: center; }
.expand.open { transform: rotate(90deg); }
.expand.placeholder { visibility: hidden; }
.node-label { flex: 1; font-size: 0.9rem; }
.region-label { font-weight: 600; }
.group-label { font-weight: 700; font-size: 1rem; }
.team-label { font-size: 0.88rem; color: var(--color-text-secondary); }
.branch-label { font-size: 0.85rem; color: var(--color-text-secondary); }
.node-badge { font-size: 0.72rem; color: var(--color-text-tertiary); background: var(--color-bg-page); border-radius: 10px; padding: 1px 7px; min-width: 20px; text-align: center; }
.tree-children { margin-left: 18px; }

.org-main { flex: 1; background: var(--color-bg-page); display: flex; flex-direction: column; overflow: hidden; }
.main-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 24px; background: var(--color-bg-card); border-bottom: 1px solid var(--color-border-light); gap: 16px; }
.header-title { display: flex; align-items: baseline; gap: 10px; }
.header-title h2 { margin: 0; font-size: 1.2rem; }
.header-count { color: var(--color-primary-600); font-weight: 600; }
.header-hint { color: var(--color-text-tertiary); font-size: 0.9rem; }
.header-actions { display: flex; gap: 8px; }
.employee-actions { display: flex; align-items: center; gap: 12px; padding: 10px 24px; border-bottom: 1px solid var(--color-border-light); background: var(--color-bg-card); }
.actions-hint { color: var(--color-text-tertiary); font-size: 0.82rem; }

.action-btn { height: 32px; padding: 0 14px; border: 1px solid var(--color-border); background: var(--color-bg-card); border-radius: 6px; cursor: pointer; font-size: 0.85rem; color: var(--color-text-primary); }
.action-btn:hover { background: var(--color-primary-50); }
.action-btn.primary { background: var(--color-primary-500); border-color: var(--color-primary-500); color: #fff; }
.action-btn.primary:hover { background: var(--color-primary-600); }
.action-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.employee-section { flex: 1; overflow-y: auto; padding: 16px 24px; }
.empty { color: var(--color-text-tertiary); padding: 40px; text-align: center; }
.empty-main { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--color-text-tertiary); }
.employee-table { width: 100%; border-collapse: collapse; background: var(--color-bg-card); border-radius: 8px; overflow: hidden; box-shadow: var(--shadow-sm); }
.employee-table th, .employee-table td { padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--color-border-light); font-size: 0.9rem; }
.employee-table th { background: var(--color-bg-page); color: var(--color-text-secondary); font-weight: 600; }
.employee-table tbody tr:hover { background: var(--color-primary-50); }
.employee-table tbody tr:last-child td { border-bottom: none; }
td.clickable { cursor: pointer; color: var(--color-primary-600); font-weight: 500; }
.row-btn { height: 26px; padding: 0 10px; border: 1px solid var(--color-border); background: transparent; border-radius: 5px; cursor: pointer; font-size: 0.8rem; margin-right: 6px; color: var(--color-text-secondary); }
.row-btn:hover { background: var(--color-primary-50); }
.row-btn.danger { color: var(--color-danger); border-color: var(--color-danger); }
.row-btn.danger:hover { background: oklch(0.95 0.08 25); }

/* 弹窗 */
.modal-mask { position: fixed; inset: 0; background: oklch(0.2 0.02 250 / 0.45); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { width: 460px; max-width: 92vw; max-height: 88vh; overflow-y: auto; background: var(--color-bg-card); border-radius: 10px; box-shadow: var(--shadow-xl); }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--color-border-light); }
.modal-header h3 { margin: 0; font-size: 1.05rem; }
.modal-close { border: none; background: none; font-size: 1.4rem; cursor: pointer; color: var(--color-text-tertiary); line-height: 1; }
.modal-body { padding: 18px 20px; display: flex; flex-direction: column; gap: 12px; }
.form-row { display: flex; flex-direction: column; gap: 4px; }
.form-row label { font-size: 0.82rem; color: var(--color-text-secondary); }
.req { color: var(--color-danger); }
.form-input { height: 36px; padding: 0 10px; border: 1px solid var(--color-border); border-radius: 6px; font-size: 0.88rem; background: var(--color-bg-page); color: var(--color-text-primary); outline: none; box-sizing: border-box; }
.form-input:focus { border-color: var(--color-primary-400); }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 20px; border-top: 1px solid var(--color-border-light); }
.move-employee-name { font-size: 0.9rem; color: var(--color-text-primary); padding: 4px 0; }
.move-team-hint { margin: 0; font-size: 0.82rem; color: var(--color-text-secondary); }

/* 员工编辑页（右侧切换） */
.employee-form-page { flex: 1; overflow-y: auto; }
.form-page-header { display: flex; align-items: center; gap: 14px; padding: 14px 24px; border-bottom: 1px solid var(--color-border-light); background: var(--color-bg-card); }
.back-btn { border: none; background: none; cursor: pointer; color: var(--color-primary-600); font-size: 0.9rem; padding: 4px 8px; border-radius: 6px; }
.back-btn:hover { background: var(--color-primary-50); }
.form-page-header h2 { margin: 0; font-size: 1.15rem; }
.form-page-body { padding: 22px 24px; max-width: 520px; display: flex; flex-direction: column; gap: 14px; }
.form-actions { display: flex; gap: 10px; margin-top: 8px; }
</style>
