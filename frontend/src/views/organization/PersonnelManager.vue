<script setup lang="ts">
import { ref, computed } from 'vue'
import { ROLE_LABELS } from '@/constants'
import { UserRole } from '@/types'
type UserRoleType = typeof UserRole[keyof typeof UserRole]

interface UserUI {
  id: string
  phone: string
  name: string
  branch?: string
  region?: string
  leader?: string
  team?: string
  role: UserRoleType
  status: string
  avatar?: string
  systemAvatar?: string
  lastLogin?: string
}

const props = defineProps<{
  users: UserUI[]
  regions: any[]
  branches: any[]
  teams: any[]
  canManageOrg: boolean
}>()

const emit = defineEmits<{
  edit: [item: any, type: string]
  delete: [item: UserUI]
  toggleStatus: [item: UserUI]
}>()

const personnelKeyword = ref('')
const personnelRoleFilter = ref('')
const personnelRegionFilter = ref('')
const personnelStatusFilter = ref('active')

const filteredUsers = computed(() => {
  let result = props.users
  if (personnelKeyword.value) {
    const kw = personnelKeyword.value.toLowerCase()
    result = result.filter(u => u.name.toLowerCase().includes(kw) || u.phone.includes(kw))
  }
  if (personnelRoleFilter.value) {
    result = result.filter(u => u.role === personnelRoleFilter.value)
  }
  if (personnelRegionFilter.value) {
    result = result.filter(u => u.region === personnelRegionFilter.value)
  }
  if (personnelStatusFilter.value) {
    result = result.filter(u => u.status === personnelStatusFilter.value)
  }
  return result
})

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

function getRegionName(id?: string) {
  if (!id) return '-'
  return props.regions.find(r => r.id === id)?.name || '-'
}

function getBranchName(id?: string) {
  if (!id) return '-'
  return props.branches.find(b => b.id === id)?.name || '-'
}

function getUserName(id?: string) {
  if (!id) return '-'
  return props.users.find(u => u.id === id)?.name || '-'
}

function getTeamName(id?: string) {
  if (!id) return '-'
  return props.teams.find(t => t.id === id)?.name || '-'
}
</script>

<template>
  <div>
    <!-- 搜索和筛选 -->
    <div class="personnel-filters">
      <div class="filter-search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="M21 21l-4.35-4.35"/>
        </svg>
        <input v-model="personnelKeyword" type="text" placeholder="搜索姓名或手机号..." class="search-input" />
      </div>
      <select v-model="personnelRoleFilter" class="filter-select">
        <option value="">全部角色</option>
        <option value="admin">超级管理员</option>
        <option value="manager">行政经理</option>
        <option value="supervisor">行政主管</option>
        <option value="leader">行政组长</option>
        <option value="staff">行政专员</option>
      </select>
      <select v-model="personnelRegionFilter" class="filter-select">
        <option value="">全部区域</option>
        <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
      </select>
      <select v-model="personnelStatusFilter" class="filter-select">
        <option value="">全部状态</option>
        <option value="active">在职</option>
        <option value="inactive">停用</option>
      </select>
    </div>

    <div v-if="filteredUsers.length === 0" class="empty-main">
      <div class="empty-content">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
          <circle cx="12" cy="7" r="4"/>
        </svg>
        <h3>暂无人员数据</h3>
        <p>{{ personnelKeyword || personnelRoleFilter || personnelRegionFilter || personnelStatusFilter ? '没有匹配的筛选结果' : '点击"新增人员"按钮添加第一个人员' }}</p>
      </div>
    </div>
    <div v-else class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>姓名</th>
            <th>手机号</th>
            <th>角色</th>
            <th>所属区域</th>
            <th>所属分公司</th>
            <th>所属组</th>
            <th>直属上级</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in filteredUsers" :key="user.id">
            <td>
              <div class="branch-name-cell">
                <span class="branch-name">{{ user.name }}</span>
              </div>
            </td>
            <td>{{ user.phone }}</td>
            <td>
              <span class="node-role" :style="getRoleStyle(user.role)">
                {{ ROLE_LABELS[user.role] || user.role }}
              </span>
            </td>
            <td>{{ getRegionName(user.region) }}</td>
            <td>{{ getBranchName(user.branch) }}</td>
            <td>{{ getTeamName(user.team) }}</td>
            <td>{{ getUserName(user.leader) }}</td>
            <td>
              <label class="status-toggle">
                <input type="checkbox" :checked="user.status === 'active'" @change="emit('toggleStatus', user)" class="toggle-input" />
                <span class="toggle-slider"></span>
              </label>
            </td>
            <td>
              <div v-if="canManageOrg" class="action-buttons">
                <button class="action-btn" title="编辑" @click="emit('edit', user, 'users')">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                  </svg>
                </button>
                <button class="action-btn danger" title="删除" @click="emit('delete', user)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
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
}

.filter-select:focus {
  border-color: var(--color-primary-300);
}

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

.node-role {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
}

.action-buttons {
  display: flex;
  gap: var(--space-1);
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

.empty-main {
  height: 300px;
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
</style>
