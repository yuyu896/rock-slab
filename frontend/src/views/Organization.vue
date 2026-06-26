<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { getRegions, createRegion, updateRegion, deleteRegion } from '@/api/regions'
import { getBranches, createBranch, updateBranch, deleteBranch } from '@/api/branches'
import { getUsers, createUser, updateUser, deleteUser } from '@/api/users'
import { getTeams, createTeam, updateTeam, deleteTeam } from '@/api/teams'
import { handleApiError } from '@/utils/request'
import { getSystemAvatarSvg, hasSystemAvatar } from '@/utils/avatar'
import { ROLE_LABELS, BRANCH_CODE_PATTERN, BRANCH_CODE_HINT } from '@/constants'
import { usePermission } from '@/hooks/usePermission'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Region, Branch, User, Team } from '@/types'
import { UserRole } from '@/types'
import OrganizationRegion from '@/views/organization/OrganizationRegion.vue'
import OrganizationBranch from '@/views/organization/OrganizationBranch.vue'
import TeamManager from '@/views/organization/TeamManager.vue'
import PersonnelManager from '@/views/organization/PersonnelManager.vue'
type UserRoleType = typeof UserRole[keyof typeof UserRole]

// 加载状态
const loading = ref(false)

// 角色权限
const { hasMinRole } = usePermission()
const canManageOrg = computed(() => hasMinRole('supervisor'))

// 当前标签页
const activeTab = ref<'orgchart' | 'regions' | 'branches' | 'teams' | 'personnel'>('orgchart')

// 非管理员用户不允许切换到管理标签页
watch(canManageOrg, (val) => {
  if (!val && ['regions', 'branches', 'teams', 'personnel'].includes(activeTab.value)) {
    activeTab.value = 'orgchart'
  }
})



// 区域数据
interface RegionUI {
  id: string
  name: string
  code: string
  manager?: string // UUID
  status: string
  createdAt?: string
}
const regions = ref<RegionUI[]>([])

// 分公司数据
interface BranchUI {
  id: string
  name: string
  code: string
  region?: string // UUID
  manager?: string // UUID
  address?: string
  phone?: string
  status: string
}
const branches = ref<BranchUI[]>([])

// 用户数据
interface UserUI {
  id: string
  phone: string
  name: string
  branch?: string // UUID
  region?: string // UUID
  leader?: string // UUID
  team?: string // UUID
  role: UserRoleType
  status: string
  avatar?: string
  systemAvatar?: string
  lastLogin?: string
}
const users = ref<UserUI[]>([])

// 行政组数据
interface TeamUI {
  id: string
  name: string
  region: string
  regionName?: string
  leader?: string
  leaderName?: string
  memberCount?: number
  status: string
}
const teams = ref<TeamUI[]>([])

// 组织架构树节点类型
type OrgNodeType = 'root' | 'person' | 'region' | 'team'

interface OrgTreeNode {
  id: string
  label: string
  nodeType: OrgNodeType
  // person 字段
  role?: UserRoleType
  avatar?: string
  systemAvatar?: string
  phone?: string
  status?: string
  region?: string
  branch?: string
  leader?: string
  team?: string
  // region 字段
  regionCode?: string
  manager?: string
  // team 字段
  teamRegion?: string
  teamLeader?: string
  memberCount?: number
  // 子节点
  children: OrgTreeNode[]
}

const supervisorUsers = computed(() => users.value.filter(u => u.role === 'supervisor' && u.status === 'active'))

// 构建组织架构树：行政经理+区域 → 行政主管+行政组 → 组长+组员
function buildOrgTree(): OrgTreeNode[] {
  const activeUsers = users.value.filter(u => u.status === 'active')
  const topLevelNodes: OrgTreeNode[] = []

  // 行政总监 / 行政经理作为顶层节点
  const managers = activeUsers.filter(u => u.role === 'manager' || u.role === 'director')
  managers.forEach(m => {
    topLevelNodes.push({
      id: m.id,
      label: m.name,
      nodeType: 'person',
      role: m.role,
      avatar: m.avatar,
      systemAvatar: m.systemAvatar,
      phone: m.phone,
      status: m.status,
      region: m.region,
      branch: m.branch,
      leader: m.leader,
      team: m.team,
      children: [],
    })
  })

  // 各区域作为顶层节点
  regions.value.forEach(r => {
    const regionNode: OrgTreeNode = {
      id: `region-${r.id}`,
      label: r.name,
      nodeType: 'region',
      regionCode: r.code,
      manager: r.manager,
      children: [],
    }

    // 该区域下的行政主管（supervisor）
    const supervisors = activeUsers.filter(u => u.role === 'supervisor' && u.region === r.id)
    supervisors.forEach(s => {
      regionNode.children.push({
        id: s.id,
        label: s.name,
        nodeType: 'person',
        role: s.role,
        avatar: s.avatar,
        systemAvatar: s.systemAvatar,
        phone: s.phone,
        status: s.status,
        region: s.region,
        branch: s.branch,
        leader: s.leader,
        team: s.team,
        children: [],
      })
    })

    // 该区域下的行政组
    const regionTeams = teams.value.filter(t => t.region === r.id && t.status === 'active')
    regionTeams.forEach(t => {
      const teamNode: OrgTreeNode = {
        id: `team-${t.id}`,
        label: t.name,
        nodeType: 'team',
        teamRegion: t.region,
        teamLeader: t.leader,
        memberCount: t.memberCount || 0,
        children: [],
      }

      // 组长 + 组员
      const teamMembers = activeUsers.filter(u => u.team === t.id)
      teamMembers.forEach(m => {
        teamNode.children.push({
          id: m.id,
          label: m.name,
          nodeType: 'person',
          role: m.role,
          avatar: m.avatar,
          systemAvatar: m.systemAvatar,
          phone: m.phone,
          status: m.status,
          region: m.region,
          branch: m.branch,
          leader: m.leader,
          team: m.team,
          children: [],
        })
      })

      regionNode.children.push(teamNode)
    })

    topLevelNodes.push(regionNode)
  })

  // 未归属人员：没有 team 和 region 归属的在职员工（排除 manager，已作为顶层节点）
  const unassigned = activeUsers.filter(
    u => !u.team && !u.region && u.role !== 'manager'
  )
  if (unassigned.length > 0) {
    const unassignedNode: OrgTreeNode = {
      id: 'unassigned',
      label: '未归属人员',
      nodeType: 'team',
      children: unassigned.map(u => ({
        id: `unassigned-${u.id}`,
        label: u.name,
        nodeType: 'person' as OrgNodeType,
        role: u.role,
        avatar: u.avatar,
        systemAvatar: u.systemAvatar,
        phone: u.phone,
        status: u.status,
        region: u.region,
        branch: u.branch,
        leader: u.leader,
        team: u.team,
        children: [],
      })),
    }
    topLevelNodes.push(unassignedNode)
  }

  return topLevelNodes
}

// 组织架构树
const orgTree = computed(() => buildOrgTree())

// 选中的节点ID（可以是用户/区域/组）
const selectedNodeId = ref<string | null>(null)

// 展开的节点ID列表
const expandedIds = ref<Set<string>>(new Set())

// 搜索关键字
const searchKeyword = ref('')

// 过滤组织架构树（根据搜索关键字）
function filterOrgTree(node: OrgTreeNode, keyword: string): OrgTreeNode | null {
  if (!keyword) return node
  const lowerKeyword = keyword.toLowerCase()

  // 先递归过滤子节点
  const filteredChildren = node.children
    .map(child => filterOrgTree(child, keyword))
    .filter((c): c is OrgTreeNode => c !== null)

  // 当前节点是否匹配（人员按名称/手机号/角色，区域/组按名称）
  const labelMatch = node.label.toLowerCase().includes(lowerKeyword)
  const phoneMatch = node.phone?.includes(keyword) || false
  const roleMatch = node.role ? (ROLE_LABELS[node.role] || '').toLowerCase().includes(lowerKeyword) : false

  if (labelMatch || phoneMatch || roleMatch || filteredChildren.length > 0) {
    return { ...node, children: filteredChildren }
  }
  return null
}

// 收集有匹配子节点的节点ID（用于自动展开）
function collectExpandedIds(nodes: OrgTreeNode[], keyword: string): string[] {
  if (!keyword) return []
  const lowerKeyword = keyword.toLowerCase()
  const ids: string[] = []

  function walk(node: OrgTreeNode): boolean {
    const childMatches = node.children.map(walk)
    const labelMatch = node.label.toLowerCase().includes(lowerKeyword)
    const phoneMatch = node.phone?.includes(keyword) || false
    const roleMatch = node.role ? (ROLE_LABELS[node.role] || '').toLowerCase().includes(lowerKeyword) : false
    const hasMatch = labelMatch || phoneMatch || roleMatch

    if (childMatches.some(Boolean)) {
      ids.push(node.id)
    }
    return hasMatch || childMatches.some(Boolean)
  }

  nodes.forEach(walk)
  return ids
}

const filteredOrgTree = computed(() => {
  const tree = orgTree.value
  if (!searchKeyword.value) return tree
  return tree
    .map(node => filterOrgTree(node, searchKeyword.value))
    .filter((n): n is OrgTreeNode => n !== null)
})

// 搜索时自动展开匹配节点的父级
watch(searchKeyword, (keyword) => {
  if (!keyword) return
  const ids = collectExpandedIds(orgTree.value, keyword)
  ids.forEach(id => expandedIds.value.add(id))
})

// 选中的用户
const selectedUser = computed(() => {
  if (!selectedNodeId.value) return null
  const userId = selectedNodeId.value.startsWith('unassigned-')
    ? selectedNodeId.value.replace('unassigned-', '')
    : selectedNodeId.value
  return users.value.find(u => u.id === userId)
})

// 选中的行政组节点
const selectedTeamNode = computed(() => {
  if (!selectedNodeId.value || !selectedNodeId.value.startsWith('team-')) return null
  const teamId = selectedNodeId.value.replace('team-', '')
  return teams.value.find(t => t.id === teamId) || null
})

// 选中的行政组成员
const teamMembers = computed(() => {
  if (!selectedTeamNode.value) return []
  const teamId = selectedNodeId.value!.replace('team-', '')
  return users.value.filter(u => u.team === teamId && u.status === 'active')
})

// 选中用户的下属
const selectedUserSubordinates = computed(() => {
  if (!selectedNodeId.value) return []
  return users.value.filter(u => u.leader === selectedNodeId.value)
})

// 统计数据
const stats = computed(() => ({
  regions: regions.value.length,
  branches: branches.value.length,
  users: users.value.length,
  activeUsers: users.value.filter(u => u.status === 'active').length
}))

// 切换节点展开/折叠
function toggleExpand(userId: string) {
  if (expandedIds.value.has(userId)) {
    expandedIds.value.delete(userId)
  } else {
    expandedIds.value.add(userId)
  }
}

// 选中用户
function selectUser(userId: string) {
  selectedNodeId.value = userId
}

// 选中节点（通用）
function selectNode(nodeId: string) {
  selectedNodeId.value = nodeId
}

// 角色样式
const getRoleStyle = (role: string) => {
  const styles: Record<string, { background: string; color: string }> = {
    'admin': { background: 'oklch(0.95 0.02 250)', color: 'oklch(0.25 0.05 250)' },
    'manager': { background: 'oklch(0.93 0.03 250)', color: 'oklch(0.30 0.06 250)' },
    'supervisor': { background: 'var(--color-primary-100)', color: 'var(--color-primary-700)' },
    'leader': { background: 'var(--color-primary-100)', color: 'var(--color-primary-700)' },
    'staff': { background: 'var(--color-bg-elevated)', color: 'var(--color-text-secondary)' }
  }
  return styles[role] || styles['staff']
}

// 递归统计节点下所有 person 类型节点数
function countPersons(node: OrgTreeNode): number {
  let count = node.nodeType === 'person' ? 1 : 0
  for (const child of node.children) {
    count += countPersons(child)
  }
  return count
}

// 头像辅助函数
function getInitial(name?: string) {
  if (!name) return '?'
  return name.charAt(0)
}

const roleBgColors: Record<string, string> = {
  'admin': 'oklch(0.20 0.04 250)',
  'manager': 'oklch(0.25 0.06 250)',
  'supervisor': 'var(--color-primary-500)',
  'leader': 'var(--color-primary-300)',
  'staff': 'var(--color-primary-100)',
}

function getAvatarStyle(node: { role?: string; nodeType?: string }) {
  const role = node.role || (node.nodeType === 'region' ? 'supervisor' : node.nodeType === 'team' ? 'leader' : 'staff')
  return {
    backgroundColor: roleBgColors[role] || 'var(--color-bg-elevated)',
  }
}

// 显示名称解析
function getRegionName(id?: string) {
  if (!id) return '-'
  return regions.value.find(r => r.id === id)?.name || '-'
}

function getBranchName(id?: string) {
  if (!id) return '-'
  return branches.value.find(b => b.id === id)?.name || '-'
}

function getUserName(id?: string) {
  if (!id) return '-'
  return users.value.find(u => u.id === id)?.name || '-'
}

// 编辑弹窗
const editingItem = ref<any>(null)
const showModal = ref(false)
const saving = ref(false)

function onCodeInput(e: Event) {
  editingItem.value.code = (e.target as HTMLInputElement).value.toUpperCase()
}

const editItem = (item: any, type: string) => {
  editingItem.value = { ...item, type }
  showModal.value = true
}

const addItem = (type: string) => {
  editingItem.value = { type, isNew: true, status: 'active', password: '123456' }
  showModal.value = true
}

// 获取区域列表
async function fetchRegions() {
  try {
    const { data } = await getRegions()
    regions.value = data
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 获取分公司列表
async function fetchBranches() {
  try {
    const { data } = await getBranches()
    branches.value = data
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 获取用户列表
async function fetchUsers() {
  try {
    const { data } = await getUsers()
    users.value = data
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 获取行政组列表
async function fetchTeams() {
  try {
    const { data } = await getTeams()
    teams.value = data
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 保存数据
async function saveItem() {
  if (!editingItem.value) return
  saving.value = true
  try {
    const item = editingItem.value
    if (item.type === 'region') {
      const payload: Record<string, unknown> = {
        name: item.name,
        code: item.code,
        manager: item.manager || null,
        status: item.status || 'active',
      }
      if (item.isNew) {
        await createRegion(payload as Partial<Region>)
      } else {
        await updateRegion(item.id, payload as Partial<Region>)
      }
      ElMessage.success(item.isNew ? '创建成功' : '保存成功')
      await fetchRegions()
    } else if (item.type === 'branch') {
      if (item.code && !new RegExp(BRANCH_CODE_PATTERN).test(item.code)) {
        ElMessage.warning(`分公司编码格式错误：${BRANCH_CODE_HINT}`)
        saving.value = false
        return
      }
      const payload: Record<string, unknown> = {
        name: item.name,
        code: item.code,
        region: item.region || null,
        address: item.address,
        phone: item.phone,
        manager: item.manager || null,
        status: item.status || 'active',
      }
      if (item.isNew) {
        await createBranch(payload)
      } else {
        await updateBranch(item.id, payload)
      }
      ElMessage.success(item.isNew ? '创建成功' : '保存成功')
      await fetchBranches()
    } else if (item.type === 'user' || item.type === 'users') {
      if (item.phone && !/^\d{11}$/.test(item.phone)) {
        ElMessage.warning('手机号必须为11位数字')
        saving.value = false
        return
      }
      const payload: Partial<User> & { password?: string } = {
        name: item.name,
        phone: item.phone,
        role: item.role as UserRoleType,
        region: item.region || null,
        branch: item.branch || null,
        team: item.team || null,
        leader: item.leader || null,
        status: item.status || 'active',
      }
      if (item.isNew) {
        payload.password = item.password || '123456'
        await createUser(payload as any)
      } else {
        await updateUser(item.id, payload)
      }
      ElMessage.success(item.isNew ? '创建成功' : '保存成功')
      await fetchUsers()
    } else if (item.type === 'team') {
      const payload = {
        name: item.name,
        region: item.region || null,
        leader: item.leader || null,
        status: item.status || 'active',
      }
      if (item.isNew) {
        await createTeam(payload)
      } else {
        await updateTeam(item.id, payload)
      }
      ElMessage.success(item.isNew ? '创建成功' : '保存成功')
      await fetchTeams()
      await fetchUsers()
    }
    showModal.value = false
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    saving.value = false
  }
}

// 删除用户
async function deleteUserItem(user: UserUI) {
  try {
    await ElMessageBox.confirm('确定删除该人员？此操作不可恢复', '删除确认', { type: 'warning' })
    await deleteUser(user.id)
    ElMessage.success('删除成功')
    if (selectedNodeId.value === user.id) {
      selectedNodeId.value = null
    }
    await fetchUsers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

// 删除行政组
async function deleteTeamItem(team: TeamUI) {
  try {
    await ElMessageBox.confirm('确定删除该行政组？删除后组成员将解除关联', '删除确认', { type: 'warning' })
    await deleteTeam(team.id)
    ElMessage.success('删除成功')
    if (selectedNodeId.value === `team-${team.id}`) {
      selectedNodeId.value = null
    }
    await fetchTeams()
    await fetchUsers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

// 切换状态（启用/停用）
async function toggleUserStatus(user: UserUI) {
  const newStatus = user.status === 'active' ? 'inactive' : 'active'
  try {
    await updateUser(user.id, {
      name: user.name,
      phone: user.phone,
      role: user.role,
      region: user.region || undefined,
      branch: user.branch || undefined,
      team: user.team || undefined,
      leader: user.leader || undefined,
      status: newStatus,
    })
    await fetchUsers()
    ElMessage.success(newStatus === 'active' ? '已启用' : '已停用')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 切换区域/分公司状态
async function toggleStatus(item: RegionUI | BranchUI, type: string) {
  const newStatus = item.status === 'active' ? 'inactive' : 'active'
  try {
    if (type === 'region') {
      await updateRegion(item.id, { status: newStatus } as any)
      await fetchRegions()
    } else if (type === 'branch') {
      await updateBranch(item.id, { status: newStatus } as any)
      await fetchBranches()
    }
    ElMessage.success(newStatus === 'active' ? '已启用' : '已停用')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 切换行政组状态
async function toggleTeamStatus(team: TeamUI) {
  const newStatus = team.status === 'active' ? 'inactive' : 'active'
  try {
    await updateTeam(team.id, { status: newStatus })
    await fetchTeams()
    ElMessage.success(newStatus === 'active' ? '已启用' : '已停用')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 删除数据
async function deleteItem(item: RegionUI | BranchUI | UserUI, type: string) {
  try {
    await ElMessageBox.confirm('确定删除？此操作不可恢复', '删除确认', { type: 'warning' })
    if (type === 'region') {
      await deleteRegion(item.id)
      ElMessage.success('删除成功')
      if (selectedNodeId.value?.startsWith('region-') && selectedNodeId.value === `region-${item.id}`) {
        selectedNodeId.value = null
      }
      await fetchRegions()
    } else if (type === 'branch') {
      await deleteBranch(item.id)
      ElMessage.success('删除成功')
      selectedNodeId.value = null
      await fetchBranches()
    } else if (type === 'user') {
      await deleteUser(item.id)
      ElMessage.success('删除成功')
      if (selectedNodeId.value === item.id) {
        selectedNodeId.value = null
      }
      await fetchUsers()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

// 初始化
onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([fetchRegions(), fetchBranches(), fetchUsers(), fetchTeams()])
    // 默认展开第一级
    orgTree.value.forEach(node => expandedIds.value.add(node.id))
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="org-layout">
    <!-- 左侧边栏 - 人员汇报树 -->
    <aside class="org-sidebar">
      <!-- 侧边栏头部 -->
      <div class="sidebar-header">
        <div class="sidebar-title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="title-icon">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg>
          <span>组织架构</span>
        </div>
        <div class="sidebar-stats">{{ stats.activeUsers }} 人</div>
      </div>

      <!-- 搜索框 -->
      <div class="sidebar-search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="M21 21l-4.35-4.35"/>
        </svg>
        <input
          v-model="searchKeyword"
          type="text"
          placeholder="搜索人员..."
          class="search-input"
        />
      </div>

      <!-- 工具栏 -->
      <div class="sidebar-toolbar">
        <span class="sidebar-title">启航事业部</span>
      </div>

      <!-- 组织架构树 -->
      <div class="sidebar-tree">
        <template v-if="loading">
          <div class="loading-state">加载中...</div>
        </template>
        <template v-else-if="filteredOrgTree.length === 0">
          <div class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <line x1="17" y1="11" x2="23" y2="11"/>
            </svg>
            <span>{{ searchKeyword ? '未找到匹配项' : '暂无组织数据' }}</span>
          </div>
        </template>

        <!-- 组织架构树 -->
        <div v-else class="tree-root">
          <div
            v-for="child in filteredOrgTree"
            :key="child.id"
            class="tree-node"
            :class="{
              selected: selectedNodeId === child.id,
              expanded: expandedIds.has(child.id)
            }"
          >
                <!-- 人员节点（行政经理） -->
                <template v-if="child.nodeType === 'person'">
                  <div class="node-content" @click="selectNode(child.id)">
                    <span
                      v-if="child.children.length > 0"
                      class="expand-btn"
                      :class="{ rotated: expandedIds.has(child.id) }"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
                    </span>
                    <span v-else class="expand-placeholder"></span>
                    <span class="node-icon avatar-icon" :style="!child.avatar && !hasSystemAvatar(child.systemAvatar) ? getAvatarStyle(child) : {}">
                      <img v-if="child.avatar" :src="child.avatar" class="avatar-img" />
                      <span v-else-if="hasSystemAvatar(child.systemAvatar)" class="avatar-svg" v-html="getSystemAvatarSvg(child.systemAvatar || '', 24)" />
                      <span v-else class="avatar-initial">{{ getInitial(child.label) }}</span>
                    </span>
                    <span class="node-name">{{ child.label }}</span>
                    <span class="node-role" :style="getRoleStyle(child.role || 'staff')">
                      {{ ROLE_LABELS[child.role || 'staff'] }}
                    </span>
                  </div>
                </template>

                <!-- 区域节点 -->
                <template v-else-if="child.nodeType === 'region'">
                  <div class="node-content" @click="toggleExpand(child.id)">
                    <span
                      class="expand-btn"
                      :class="{ rotated: expandedIds.has(child.id) }"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
                    </span>
                    <span class="node-icon region-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                        <circle cx="12" cy="10" r="3"/>
                      </svg>
                    </span>
                    <span class="node-name">{{ child.label }}</span>
                    <span class="node-count">{{ countPersons(child) }}</span>
                  </div>

                  <!-- 第三层：行政主管 + 行政组 -->
                  <div v-if="expandedIds.has(child.id)" class="tree-children">
                    <div
                      v-for="subChild in child.children"
                      :key="subChild.id"
                      class="tree-node"
                      :class="{
                        selected: selectedNodeId === subChild.id,
                        expanded: expandedIds.has(subChild.id)
                      }"
                    >
                      <!-- 人员节点（行政主管） -->
                      <template v-if="subChild.nodeType === 'person'">
                        <div class="node-content" @click="selectNode(subChild.id)">
                          <span class="expand-placeholder"></span>
                          <span class="node-icon avatar-icon" :style="!subChild.avatar && !hasSystemAvatar(subChild.systemAvatar) ? getAvatarStyle(subChild) : {}">
                            <img v-if="subChild.avatar" :src="subChild.avatar" class="avatar-img" />
                            <span v-else-if="hasSystemAvatar(subChild.systemAvatar)" class="avatar-svg" v-html="getSystemAvatarSvg(subChild.systemAvatar || '', 24)" />
                            <span v-else class="avatar-initial">{{ getInitial(subChild.label) }}</span>
                          </span>
                          <span class="node-name">{{ subChild.label }}</span>
                          <span class="node-role" :style="getRoleStyle(subChild.role || 'staff')">
                            {{ ROLE_LABELS[subChild.role || 'staff'] }}
                          </span>
                        </div>
                      </template>

                      <!-- 行政组节点 -->
                      <template v-else-if="subChild.nodeType === 'team'">
                        <div class="node-content" @click="toggleExpand(subChild.id)">
                          <span
                            v-if="subChild.children.length > 0"
                            class="expand-btn"
                            :class="{ rotated: expandedIds.has(subChild.id) }"
                          >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
                          </span>
                          <span v-else class="expand-placeholder"></span>
                          <span class="node-icon team-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                              <circle cx="9" cy="7" r="4"/>
                              <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
                            </svg>
                          </span>
                          <span class="node-name">{{ subChild.label }}</span>
                          <span class="node-count">{{ countPersons(subChild) }}</span>
                        </div>

                        <!-- 第四层：组长 + 组员 -->
                        <div v-if="expandedIds.has(subChild.id)" class="tree-children">
                          <div
                            v-for="member in subChild.children"
                            :key="member.id"
                            class="tree-node"
                            :class="{ selected: selectedNodeId === member.id }"
                          >
                            <div class="node-content" @click="selectNode(member.id)">
                              <span class="expand-placeholder"></span>
                              <span class="node-icon avatar-icon" :style="!member.avatar && !hasSystemAvatar(member.systemAvatar) ? getAvatarStyle(member) : {}">
                                <img v-if="member.avatar" :src="member.avatar" class="avatar-img" />
                                <span v-else-if="hasSystemAvatar(member.systemAvatar)" class="avatar-svg" v-html="getSystemAvatarSvg(member.systemAvatar || '', 24)" />
                                <span v-else class="avatar-initial">{{ getInitial(member.label) }}</span>
                              </span>
                              <span class="node-name">{{ member.label }}</span>
                              <span class="node-role" :style="getRoleStyle(member.role || 'staff')">
                                {{ ROLE_LABELS[member.role || 'staff'] }}
                              </span>
                            </div>
                          </div>
                        </div>
                      </template>
                    </div>
                  </div>
                </template>

                <!-- 未归属人员节点（team 类型在顶层） -->
                <template v-else-if="child.nodeType === 'team'">
                  <div class="node-content" @click="toggleExpand(child.id)">
                    <span
                      class="expand-btn"
                      :class="{ rotated: expandedIds.has(child.id) }"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
                    </span>
                    <span class="node-icon team-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                        <circle cx="9" cy="7" r="4"/>
                        <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
                      </svg>
                    </span>
                    <span class="node-name">{{ child.label }}</span>
                    <span class="node-count">{{ countPersons(child) }}</span>
                  </div>

                  <div v-if="expandedIds.has(child.id)" class="tree-children">
                    <div
                      v-for="member in child.children"
                      :key="member.id"
                      class="tree-node"
                      :class="{ selected: selectedNodeId === member.id }"
                    >
                      <div class="node-content" @click="selectNode(member.id)">
                        <span class="expand-placeholder"></span>
                        <span class="node-icon avatar-icon" :style="!member.avatar && !hasSystemAvatar(member.systemAvatar) ? getAvatarStyle(member) : {}">
                          <img v-if="member.avatar" :src="member.avatar" class="avatar-img" />
                          <span v-else-if="hasSystemAvatar(member.systemAvatar)" class="avatar-svg" v-html="getSystemAvatarSvg(member.systemAvatar || '', 24)" />
                          <span v-else class="avatar-initial">{{ getInitial(member.label) }}</span>
                        </span>
                        <span class="node-name">{{ member.label }}</span>
                        <span class="node-role" :style="getRoleStyle(member.role || 'staff')">
                          {{ ROLE_LABELS[member.role || 'staff'] }}
                        </span>
                      </div>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>
    </aside>

    <!-- 主内容区 -->
    <main class="org-main">
      <!-- 标签页导航 -->
      <div class="main-tabs">
        <button class="main-tab" :class="{ active: activeTab === 'orgchart' }" @click="activeTab = 'orgchart'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg>
          组织架构
        </button>
        <button v-if="canManageOrg" class="main-tab" :class="{ active: activeTab === 'regions' }" @click="activeTab = 'regions'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
            <circle cx="12" cy="10" r="3"/>
          </svg>
          区域管理
        </button>
        <button v-if="canManageOrg" class="main-tab" :class="{ active: activeTab === 'branches' }" @click="activeTab = 'branches'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
            <polyline points="9 22 9 12 15 12 15 22"/>
          </svg>
          分公司管理
        </button>
        <button v-if="canManageOrg" class="main-tab" :class="{ active: activeTab === 'teams' }" @click="activeTab = 'teams'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg>
          行政组
        </button>
        <button v-if="canManageOrg" class="main-tab" :class="{ active: activeTab === 'personnel' }" @click="activeTab = 'personnel'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
          人员管理
        </button>
        <div class="tab-actions">
          <button v-if="activeTab === 'regions'" class="btn-add" @click="addItem('region')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            新增区域
          </button>
          <button v-if="activeTab === 'branches'" class="btn-add" @click="addItem('branch')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            新增分公司
          </button>
          <button v-if="activeTab === 'teams'" class="btn-add" @click="addItem('team')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            新增行政组
          </button>
          <button v-if="canManageOrg && activeTab === 'personnel'" class="btn-add" @click="addItem('users')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            新增人员
          </button>
        </div>
      </div>

      <!-- 组织架构内容 -->
      <div v-if="activeTab === 'orgchart'" class="tab-content">
        <!-- 未选中状态 -->
        <div v-if="!selectedUser && !selectedTeamNode" class="empty-main">
          <div class="empty-content">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
            <h3>选择节点查看详情</h3>
            <p>从左侧列表中选择人员或行政组，查看详细信息</p>
          </div>
        </div>

        <!-- 行政组详情 -->
        <div v-else-if="selectedTeamNode" class="user-detail">
          <div class="detail-header">
            <div class="user-profile">
              <div class="profile-avatar team-detail-avatar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="32" height="32" style="color: var(--color-primary-500)">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                  <circle cx="9" cy="7" r="4"/>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
              </div>
              <div class="profile-info">
                <h2 class="profile-name">{{ selectedTeamNode.name }}</h2>
                <span class="profile-role" :style="getRoleStyle('leader')">行政组</span>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h3 class="section-title">基本信息</h3>
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">组名</span>
                <span class="info-value">{{ selectedTeamNode.name }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">所属区域</span>
                <span class="info-value">{{ getRegionName(selectedTeamNode.region) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">组长</span>
                <span class="info-value">{{ getUserName(selectedTeamNode.leader) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">组员数量</span>
                <span class="info-value">{{ selectedTeamNode.memberCount || 0 }} 人</span>
              </div>
            </div>
          </div>

          <div v-if="teamMembers.length > 0" class="detail-section">
            <h3 class="section-title">
              组员列表
              <span class="section-count">{{ teamMembers.length }} 人</span>
            </h3>
            <div class="subordinate-list">
              <div
                v-for="member in teamMembers"
                :key="member.id"
                class="subordinate-item"
                @click="selectNode(member.id)"
              >
                <div class="sub-avatar" :style="!member.avatar && !hasSystemAvatar(member.systemAvatar) ? getAvatarStyle(member) : {}">
                  <img v-if="member.avatar" :src="member.avatar" class="avatar-img" />
                  <span v-else-if="hasSystemAvatar(member.systemAvatar)" class="avatar-svg" v-html="getSystemAvatarSvg(member.systemAvatar || '', 36)" />
                  <span v-else class="avatar-initial">{{ getInitial(member.name) }}</span>
                </div>
                <div class="sub-info">
                  <span class="sub-name">{{ member.name }}</span>
                  <span class="sub-role" :style="getRoleStyle(member.role)">
                    {{ ROLE_LABELS[member.role] || member.role }}
                  </span>
                </div>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="sub-arrow">
                  <path d="M9 18l6-6-6-6"/>
                </svg>
              </div>
            </div>
          </div>
        </div>

        <!-- 人员详情 -->
        <div v-else-if="selectedUser" class="user-detail">
          <!-- 头部 -->
          <div class="detail-header">
            <div class="user-profile">
              <div class="profile-avatar" :style="!selectedUser.avatar && !hasSystemAvatar(selectedUser.systemAvatar) ? getAvatarStyle(selectedUser) : {}">
                <img v-if="selectedUser.avatar" :src="selectedUser.avatar" class="avatar-img" />
                <span v-else-if="hasSystemAvatar(selectedUser.systemAvatar)" class="avatar-svg" v-html="getSystemAvatarSvg(selectedUser.systemAvatar || '', 64)" />
                <span v-else class="avatar-initial">{{ getInitial(selectedUser.name) }}</span>
              </div>
              <div class="profile-info">
                <h2 class="profile-name">{{ selectedUser.name }}</h2>
                <span class="profile-role" :style="getRoleStyle(selectedUser.role)">
                  {{ ROLE_LABELS[selectedUser.role] || selectedUser.role }}
                </span>
              </div>
            </div>
          </div>

          <!-- 基本信息 -->
          <div class="detail-section">
            <h3 class="section-title">基本信息</h3>
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">手机号</span>
                <span class="info-value">{{ selectedUser.phone }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">所属区域</span>
                <span class="info-value">{{ getRegionName(selectedUser.region) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">所属分公司</span>
                <span class="info-value">{{ getBranchName(selectedUser.branch) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">直属上级</span>
                <span class="info-value">{{ getUserName(selectedUser.leader) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">账号状态</span>
                <span class="info-value">{{ selectedUser.status === 'active' ? '在职' : '已停用' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">最后登录</span>
                <span class="info-value">{{ selectedUser.lastLogin || '从未登录' }}</span>
              </div>
            </div>
          </div>

          <!-- 下属列表 -->
          <div v-if="selectedUserSubordinates.length > 0" class="detail-section">
            <h3 class="section-title">
              下属列表
              <span class="section-count">{{ selectedUserSubordinates.length }} 人</span>
            </h3>
            <div class="subordinate-list">
              <div
                v-for="sub in selectedUserSubordinates"
                :key="sub.id"
                class="subordinate-item"
                @click="selectUser(sub.id)"
              >
                <div class="sub-avatar" :style="!sub.avatar && !hasSystemAvatar(sub.systemAvatar) ? getAvatarStyle(sub) : {}">
                  <img v-if="sub.avatar" :src="sub.avatar" class="avatar-img" />
                  <span v-else-if="hasSystemAvatar(sub.systemAvatar)" class="avatar-svg" v-html="getSystemAvatarSvg(sub.systemAvatar || '', 36)" />
                  <span v-else class="avatar-initial">{{ getInitial(sub.name) }}</span>
                </div>
                <div class="sub-info">
                  <span class="sub-name">{{ sub.name }}</span>
                  <span class="sub-role" :style="getRoleStyle(sub.role)">
                    {{ ROLE_LABELS[sub.role] || sub.role }}
                  </span>
                </div>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="sub-arrow">
                  <path d="M9 18l6-6-6-6"/>
                </svg>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 区域管理内容 -->
      <div v-else-if="canManageOrg && activeTab === 'regions'" class="tab-content">
        <OrganizationRegion
          :regions="regions"
          :users="users"
          :branches="branches"
          @edit="(item) => editItem(item, 'region')"
          @delete="(item) => deleteItem(item, 'region')"
          @toggle-status="(item) => toggleStatus(item, 'region')"
        />
      </div>

      <!-- 分公司管理内容 -->
      <div v-else-if="canManageOrg && activeTab === 'branches'" class="tab-content">
        <OrganizationBranch
          :branches="branches"
          :regions="regions"
          :users="users"
          @edit="(item) => editItem(item, 'branch')"
          @delete="(item) => deleteItem(item, 'branch')"
          @toggle-status="(item) => toggleStatus(item, 'branch')"
        />
      </div>

      <!-- 行政组管理内容 -->
      <div v-else-if="canManageOrg && activeTab === 'teams'" class="tab-content">
        <TeamManager
          :teams="teams"
          :users="users"
          :can-manage-org="canManageOrg"
          @edit="(item) => editItem(item, 'team')"
          @delete="(item) => deleteTeamItem(item)"
          @toggle-status="(item) => toggleTeamStatus(item)"
        />
      </div>

      <!-- 人员管理内容 -->
      <div v-else-if="canManageOrg && activeTab === 'personnel'" class="tab-content">
        <PersonnelManager
          :users="users"
          :regions="regions"
          :branches="branches"
          :teams="teams"
          :can-manage-org="canManageOrg"
          @edit="(item) => editItem(item, 'users')"
          @delete="(item) => deleteUserItem(item)"
          @toggle-status="(item) => toggleUserStatus(item)"
        />
      </div>
    </main>

    <!-- 编辑弹窗 -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3 class="modal-title">
            {{ editingItem?.isNew ? '新增' : '编辑' }}{{ editingItem?.type === 'region' ? '区域' : editingItem?.type === 'branch' ? '分公司' : editingItem?.type === 'team' ? '行政组' : '人员' }}
          </h3>
          <button class="modal-close" @click="showModal = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <!-- 区域表单 -->
          <template v-if="editingItem?.type === 'region' || editingItem?.type === 'regions'">
            <div class="form-grid">
              <div class="form-item">
                <label class="form-label">区域名称 <span class="required">*</span></label>
                <input v-model="editingItem.name" type="text" class="form-input" placeholder="请输入区域名称" />
              </div>
              <div class="form-item">
                <label class="form-label">区域编码 <span class="required">*</span></label>
                <input v-model="editingItem.code" type="text" class="form-input" placeholder="如：HD" />
              </div>
              <div class="form-item full">
                <label class="form-label">区域负责人 <span class="required">*</span></label>
                <select v-model="editingItem.manager" class="form-select">
                  <option value="">请选择负责人</option>
                  <option v-for="u in supervisorUsers" :key="u.id" :value="u.id">{{ u.name }} ({{ u.phone }})</option>
                </select>
              </div>
            </div>
          </template>

          <!-- 分公司表单 -->
          <template v-else-if="editingItem?.type === 'branch' || editingItem?.type === 'branches'">
            <div class="form-grid">
              <div class="form-item">
                <label class="form-label">分公司名称 <span class="required">*</span></label>
                <input v-model="editingItem.name" type="text" class="form-input" />
              </div>
              <div class="form-item">
                <label class="form-label">分公司编码 <span class="required">*</span></label>
                <input v-model="editingItem.code" type="text" class="form-input" :pattern="BRANCH_CODE_PATTERN" :placeholder="BRANCH_CODE_HINT" @input="onCodeInput" />
              </div>
              <div class="form-item">
                <label class="form-label">所属区域 <span class="required">*</span></label>
                <select v-model="editingItem.region" class="form-select">
                  <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
                </select>
              </div>
              <div class="form-item">
                <label class="form-label">负责人 <span class="required">*</span></label>
                <select v-model="editingItem.manager" class="form-select">
                  <option value="">请选择负责人</option>
                  <option v-for="u in users.filter(u => ['admin', 'director', 'manager', 'supervisor', 'leader'].includes(u.role))" :key="u.id" :value="u.id">{{ u.name }} ({{ ROLE_LABELS[u.role] || u.role }})</option>
                </select>
              </div>
              <div class="form-item full">
                <label class="form-label">地址</label>
                <input v-model="editingItem.address" type="text" class="form-input" />
              </div>
              <div class="form-item">
                <label class="form-label">联系电话</label>
                <input v-model="editingItem.phone" type="tel" maxlength="11" class="form-input" />
              </div>
            </div>
          </template>

          <!-- 人员表单 -->
          <template v-else-if="editingItem?.type === 'user' || editingItem?.type === 'users'">
            <div class="form-grid">
              <div class="form-item">
                <label class="form-label">姓名 <span class="required">*</span></label>
                <input v-model="editingItem.name" type="text" class="form-input" />
              </div>
              <div class="form-item">
                <label class="form-label">手机号 <span class="required">*</span></label>
                <input v-model="editingItem.phone" type="tel" maxlength="11" class="form-input" />
              </div>
              <div class="form-item">
                <label class="form-label">角色 <span class="required">*</span></label>
                <select v-model="editingItem.role" class="form-select">
                  <option value="admin">超级管理员</option>
                  <option value="director">行政总监</option>
                  <option value="manager">行政经理</option>
                  <option value="supervisor">行政主管</option>
                  <option value="leader">行政组长</option>
                  <option value="staff">行政专员</option>
                </select>
              </div>
              <div class="form-item">
                <label class="form-label">所属区域 <span class="required">*</span></label>
                <select v-model="editingItem.region" class="form-select">
                  <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
                </select>
              </div>
              <div class="form-item">
                <label class="form-label">所属分公司</label>
                <select v-model="editingItem.branch" class="form-select">
                  <option value="">请选择</option>
                  <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
                </select>
              </div>
              <div class="form-item">
                <label class="form-label">所属组</label>
                <select v-model="editingItem.team" class="form-select">
                  <option value="">请选择</option>
                  <option v-for="t in teams" :key="t.id" :value="t.id">{{ t.name }}</option>
                </select>
              </div>
              <div class="form-item">
                <label class="form-label">直属上级</label>
                <select v-model="editingItem.leader" class="form-select">
                  <option value="">请选择</option>
                  <option v-for="u in users.filter(u => ['admin', 'director', 'manager', 'supervisor', 'leader'].includes(u.role))" :key="u.id" :value="u.id">
                    {{ u.name }} ({{ ROLE_LABELS[u.role] || u.role }})
                  </option>
                </select>
              </div>
            </div>
          </template>

          <!-- 行政组表单 -->
          <template v-else-if="editingItem?.type === 'team'">
            <div class="form-grid">
              <div class="form-item">
                <label class="form-label">组名 <span class="required">*</span></label>
                <input v-model="editingItem.name" type="text" class="form-input" placeholder="请输入组名" />
              </div>
              <div class="form-item">
                <label class="form-label">所属区域 <span class="required">*</span></label>
                <select v-model="editingItem.region" class="form-select">
                  <option value="">请选择区域</option>
                  <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
                </select>
              </div>
              <div class="form-item">
                <label class="form-label">组长</label>
                <select v-model="editingItem.leader" class="form-select">
                  <option value="">请选择组长</option>
                  <option v-for="u in users.filter(u => u.role === 'leader')" :key="u.id" :value="u.id">
                    {{ u.name }}
                  </option>
                </select>
              </div>
            </div>
          </template>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="showModal = false">取消</button>
          <button class="btn-confirm" @click="saveItem" :disabled="saving">{{ saving ? '保存中...' : '确定保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 布局 */
.org-layout {
  display: flex;
  height: calc(100vh - var(--space-6) * 2);
  margin: calc(-1 * var(--space-6));
  background: var(--color-bg-page);
}

/* 左侧边栏 */
.org-sidebar {
  width: 280px;
  background: var(--color-bg-card);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 600;
  color: var(--color-text-primary);
}

.title-icon {
  width: 20px;
  height: 20px;
  color: var(--color-primary-500);
}

.sidebar-stats {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  background: var(--color-bg-elevated);
  padding: 2px 8px;
  border-radius: 10px;
}

.sidebar-search {
  padding: var(--space-3) var(--space-4);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.sidebar-search svg {
  width: 16px;
  height: 16px;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  outline: none;
}

.search-input::placeholder {
  color: var(--color-text-tertiary);
}

.sidebar-toolbar {
  padding: var(--space-2) var(--space-4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--color-border);
}

.sidebar-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.toolbar-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.toolbar-btn:hover {
  background: var(--color-bg-elevated);
  color: var(--color-text-primary);
}

.toolbar-btn.primary {
  background: var(--color-primary-500);
  color: white;
  margin-left: auto;
}

.toolbar-btn.primary:hover {
  background: var(--color-primary-600);
}

.toolbar-btn svg {
  width: 16px;
  height: 16px;
}

/* 人员树 */
.sidebar-tree {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2);
}

.tree-root {
  display: flex;
  flex-direction: column;
}

.tree-node {
  border-radius: 8px;
  margin-bottom: 2px;
}

.tree-node.selected > .node-content {
  background: var(--color-primary-50);
  color: var(--color-primary-700);
}

.tree-node.expanded > .node-content .expand-btn svg {
  transform: rotate(90deg);
}

.node-content {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: 6px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.node-content:hover {
  background: var(--color-bg-elevated);
}

.expand-btn {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.expand-btn svg {
  width: 12px;
  height: 12px;
  color: var(--color-text-tertiary);
  transition: transform var(--transition-fast);
}

.expand-placeholder {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.node-icon {
  width: 24px;
  height: 24px;
  text-align: center;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.avatar-icon {
  border-radius: 50%;
  overflow: hidden;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.avatar-svg {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-initial {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  border-radius: 50%;
}

.node-name {
  flex: 1;
  font-size: 15px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-role {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
}

.node-count {
  font-size: 12px;
  color: var(--color-text-tertiary);
  background: var(--color-bg-elevated);
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}

.tree-children {
  padding-left: var(--space-4);
}

.tree-node.child .node-content {
  padding-left: var(--space-2);
}

/* 加载和空状态 */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  text-align: center;
  gap: var(--space-2);
}

.empty-state svg {
  width: 40px;
  height: 40px;
  opacity: 0.5;
}

/* 主内容区 */
.org-main {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

/* 标签页导航 */
.main-tabs {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: 0 var(--space-4);
  height: 44px;
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.main-tab {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: 32px;
  padding: 0 var(--space-3);
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.main-tab:hover {
  background: var(--color-bg-elevated);
  color: var(--color-text-primary);
}

.main-tab.active {
  background: var(--color-primary-50);
  color: var(--color-primary-600);
}

.main-tab svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.tab-actions {
  margin-left: auto;
  display: flex;
  gap: var(--space-2);
}

.btn-add {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  height: 32px;
  padding: 0 var(--space-3);
  background: var(--color-primary-500);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-add:hover {
  background: var(--color-primary-600);
}

.btn-add svg {
  width: 14px;
  height: 14px;
}

/* Tab content */
.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
}

/* 筛选栏 */
.filter-bar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 0 var(--space-3);
  height: 36px;
}

.filter-item svg {
  width: 16px;
  height: 16px;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.filter-item input {
  border: none;
  background: transparent;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  outline: none;
  min-width: 160px;
}

.filter-item input::placeholder {
  color: var(--color-text-tertiary);
}

.filter-select {
  height: 36px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-card);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  cursor: pointer;
  outline: none;
  min-width: 100px;
}

.filter-select:focus {
  border-color: var(--color-primary-300);
}

/* 区域卡片 */
.region-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-4);
}

.region-card {
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  padding: var(--space-4);
  transition: all var(--transition-fast);
}

.region-card:hover {
  box-shadow: var(--shadow-md);
}

.region-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-3);
}

.region-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.region-name {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.region-code {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  background: var(--color-bg-elevated);
  padding: 2px 8px;
  border-radius: 4px;
}

.region-actions {
  display: flex;
  gap: var(--space-1);
}

.card-action-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.card-action-btn:hover {
  background: var(--color-bg-elevated);
  color: var(--color-primary-500);
}

.card-action-btn svg {
  width: 14px;
  height: 14px;
}

.region-manager {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-bg-page);
  border-radius: 8px;
  margin-bottom: var(--space-3);
}

.manager-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary-400), var(--color-primary-600));
  color: white;
  font-weight: 600;
  font-size: var(--text-sm);
  display: flex;
  align-items: center;
  justify-content: center;
}

.manager-info {
  display: flex;
  flex-direction: column;
}

.manager-name {
  font-weight: 500;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.manager-role {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.region-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.region-stat {
  text-align: center;
  padding: var(--space-2);
  background: var(--color-bg-page);
  border-radius: 6px;
}

.stat-num {
  display: block;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.region-footer {
  display: flex;
  justify-content: flex-end;
}

/* 人员管理筛选栏 */
.personnel-filters {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.filter-search {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 0 var(--space-3);
  height: 36px;
}

.filter-search svg {
  width: 16px;
  height: 16px;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.filter-select {
  height: 36px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-card);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  cursor: pointer;
}

.action-buttons {
  display: flex;
  gap: var(--space-1);
}

/* 数据表格 */
.table-container {
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  background: var(--color-bg-elevated);
  padding: var(--space-3) var(--space-4);
  text-align: left;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border);
}

.data-table td {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border-light);
  vertical-align: middle;
}

.data-table tbody tr:hover {
  background: var(--color-bg-elevated);
}

.branch-name-cell {
  display: flex;
  flex-direction: column;
}

.branch-name {
  font-weight: 500;
}

.branch-address {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.branch-code {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.region-tag {
  display: inline-block;
  padding: 4px 10px;
  background: var(--color-primary-50);
  color: var(--color-primary-600);
  border-radius: 6px;
  font-size: var(--text-xs);
}

.leader-cell {
  display: flex;
  flex-direction: column;
}

.leader-name {
  font-weight: 500;
}

.leader-role {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.empty-main {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-content {
  text-align: center;
  color: var(--color-text-tertiary);
}

.empty-content svg {
  width: 64px;
  height: 64px;
  margin-bottom: var(--space-4);
  opacity: 0.4;
}

.empty-content h3 {
  font-size: var(--text-lg);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-2) 0;
}

.empty-content p {
  font-size: var(--text-sm);
  margin: 0;
}

/* 用户详情 */
.user-detail {
  max-width: 800px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
}

.detail-actions {
  display: flex;
  gap: var(--space-2);
  flex-shrink: 0;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.profile-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  overflow: hidden;
  background: linear-gradient(135deg, var(--color-primary-400), var(--color-primary-600));
  color: white;
  font-size: var(--text-2xl);
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.profile-avatar .avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-avatar .avatar-initial {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-2xl);
  font-weight: 600;
  color: #fff;
}

.profile-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-1);
}

.profile-name {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.profile-role {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  padding: 2px 0;
  width: fit-content;
}

.header-actions {
  display: flex;
  gap: var(--space-2);
}

.action-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: 40px;
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.action-btn:hover {
  background: var(--color-bg-elevated);
  border-color: var(--color-primary-300);
}

.action-btn.danger:hover {
  background: var(--color-danger-bg);
  border-color: var(--color-danger);
  color: var(--color-danger);
}

.action-btn svg {
  width: 20px;
  height: 20px;
}

/* 详情区块 */
.detail-section {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: var(--space-5);
  margin-bottom: var(--space-4);
}

.section-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4) 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.section-count {
  font-size: var(--text-sm);
  font-weight: 400;
  color: var(--color-text-tertiary);
  background: var(--color-bg-elevated);
  padding: 2px 8px;
  border-radius: 10px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.info-label {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

.info-value {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  font-weight: 500;
}

/* 下属列表 */
.subordinate-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.subordinate-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-bg-page);
  border-radius: 8px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.subordinate-item:hover {
  background: var(--color-bg-elevated);
}

.sub-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  overflow: hidden;
  background: linear-gradient(135deg, var(--color-primary-300), var(--color-primary-500));
  color: white;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sub-avatar .avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.sub-avatar .avatar-initial {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: 600;
  color: #fff;
}

.sub-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.sub-name {
  font-weight: 500;
  color: var(--color-text-primary);
}

.sub-role {
  font-size: var(--text-xs);
  padding: 2px 6px;
  border-radius: 4px;
  width: fit-content;
  margin-top: 2px;
}

.sub-arrow {
  width: 16px;
  height: 16px;
  color: var(--color-text-tertiary);
}

/* 状态开关 */
.status-toggle {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
}

.toggle-input {
  display: none;
}

.toggle-slider {
  width: 36px;
  height: 20px;
  background: var(--color-border);
  border-radius: 10px;
  position: relative;
  transition: background var(--transition-fast);
}

.toggle-slider::after {
  content: '';
  width: 16px;
  height: 16px;
  background: var(--color-bg-card);
  border-radius: 50%;
  position: absolute;
  top: 2px;
  left: 2px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
  transition: transform var(--transition-fast);
}

.toggle-input:checked + .toggle-slider {
  background: var(--color-primary-500);
}

.toggle-input:checked + .toggle-slider::after {
  transform: translateX(16px);
}

.toggle-label {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  width: 560px;
  background: var(--color-bg-card);
  border-radius: 16px;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.modal-title {
  font-size: var(--text-lg);
  font-weight: 600;
  margin: 0;
}

.modal-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: var(--color-text-tertiary);
  cursor: pointer;
}

.modal-close svg {
  width: 18px;
  height: 18px;
}

.modal-body {
  padding: var(--space-5);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-item.full {
  grid-column: span 2;
}

.form-label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-primary);
}

.required {
  color: var(--color-danger);
}

.form-input,
.form-select {
  height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-page);
  font-size: var(--text-sm);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-5);
  border-top: 1px solid var(--color-border);
}

.btn-cancel,
.btn-confirm {
  height: 40px;
  padding: 0 var(--space-5);
  border-radius: 8px;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
}

.btn-cancel {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
}

.btn-confirm {
  background: var(--color-primary-500);
  border: none;
  color: white;
}

.btn-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 响应式 */
@media (max-width: 768px) {
  .org-layout {
    flex-direction: column;
    height: auto;
  }

  .org-sidebar {
    width: 100%;
    height: 300px;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
