<script setup lang="ts">
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

interface UserUI {
  id: string
  phone: string
  name: string
  role: string
  status: string
  avatar?: string
  systemAvatar?: string
  team?: string
}

defineProps<{
  teams: TeamUI[]
  users: UserUI[]
  canManageOrg: boolean
}>()

const emit = defineEmits<{
  edit: [item: any, type: string]
  toggleStatus: [item: TeamUI]
  delete: [item: TeamUI]
}>()

function getUserName(users: UserUI[], id?: string) {
  if (!id) return '-'
  return users.find(u => u.id === id)?.name || '-'
}

function getRegionName(regions: any[], id?: string) {
  if (!id) return '-'
  return regions.find(r => r.id === id)?.name || '-'
}
</script>

<template>
  <div class="tab-content-inner">
    <div v-if="teams.length === 0" class="empty-main">
      <div class="empty-content">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
          <circle cx="9" cy="7" r="4"/>
          <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
        </svg>
        <h3>暂无行政组</h3>
        <p>点击"新增行政组"按钮创建第一个行政组</p>
      </div>
    </div>
    <div v-else class="region-grid">
      <div v-for="team in teams" :key="team.id" class="region-card">
        <div class="region-header">
          <div class="region-info">
            <h3 class="region-name">{{ team.name }}</h3>
            <span class="region-code">{{ team.regionName || '-' }}</span>
          </div>
          <div v-if="canManageOrg" class="region-actions">
            <button class="card-action-btn" title="编辑" @click="emit('edit', team, 'team')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
            </button>
            <button class="card-action-btn" title="删除" @click="emit('delete', team)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
          </div>
        </div>

        <div class="region-manager">
          <div class="manager-avatar">{{ getUserName(users, team.leader).charAt(0) }}</div>
          <div class="manager-info">
            <span class="manager-name">{{ getUserName(users, team.leader) }}</span>
            <span class="manager-role">组长</span>
          </div>
        </div>

        <div class="region-stats">
          <div class="region-stat">
            <span class="stat-num">{{ users.filter(u => u.team === team.id && u.status === 'active').length }}</span>
            <span class="stat-label">组员</span>
          </div>
        </div>

        <div class="region-footer">
          <label class="status-toggle">
            <input type="checkbox" :checked="team.status === 'active'" @change="emit('toggleStatus', team)" class="toggle-input" />
            <span class="toggle-slider"></span>
            <span class="toggle-label">{{ team.status === 'active' ? '运营中' : '已停用' }}</span>
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tab-content-inner {
  height: 100%;
}

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
</style>
