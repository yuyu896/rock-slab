<script setup lang="ts">
defineProps<{
  branches: any[]
  regions: any[]
  users: any[]
}>()

const emit = defineEmits<{
  edit: [item: any, type: string]
  delete: [item: any, type: string]
  toggleStatus: [item: any, type: string]
}>()

function getRegionName(regions: any[], id?: string) {
  if (!id) return '-'
  return regions.find(r => r.id === id)?.name || '-'
}

function getUserName(users: any[], id?: string) {
  if (!id) return '-'
  return users.find(u => u.id === id)?.name || '-'
}
</script>

<template>
  <div>
    <div v-if="branches.length === 0" class="empty-main">
      <div class="empty-content">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
        <h3>暂无分公司数据</h3>
        <p>点击"新增分公司"按钮创建第一个分公司</p>
      </div>
    </div>
    <div v-else class="table-container">
    <table class="data-table">
      <thead>
        <tr>
          <th>分公司</th>
          <th>编码</th>
          <th>所属区域</th>
          <th>负责人</th>
          <th>人员数</th>
          <th>资产数</th>
          <th>联系方式</th>
          <th>状态</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="branch in branches" :key="branch.id">
          <td>
            <div class="branch-name-cell">
              <span class="branch-name">{{ branch.name }}</span>
              <span class="branch-address">{{ branch.address }}</span>
            </div>
          </td>
          <td>
            <span class="branch-code">{{ branch.code }}</span>
          </td>
          <td>
            <span class="region-tag">{{ getRegionName(regions, branch.region) }}</span>
          </td>
          <td>
            <div class="leader-cell">
              <span class="leader-name">{{ getUserName(users, branch.manager) }}</span>
            </div>
          </td>
          <td>-</td>
          <td>-</td>
          <td>{{ branch.phone }}</td>
          <td>
            <label class="status-toggle">
              <input type="checkbox" :checked="branch.status === 'active'" @change="emit('toggleStatus', branch, 'branch')" class="toggle-input" />
              <span class="toggle-slider"></span>
            </label>
          </td>
          <td>
            <div class="action-buttons">
              <button class="action-btn" title="编辑" @click="emit('edit', branch, 'branch')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
              <button class="action-btn" title="删除" @click="emit('delete', branch, 'branch')">
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
