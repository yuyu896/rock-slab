<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeTab = computed(() => {
  const path = route.path
  if (path.includes('/mobile/home')) return 'home'
  if (path.includes('/mobile/assets') || path.includes('/mobile/scan')) return 'assets'
  if (path.includes('/mobile/inventory')) return 'inventory'
  if (path.includes('/mobile/approval')) return 'approval'
  if (path.includes('/mobile/profile')) return 'profile'
  return 'home'
})

const tabs = [
  { key: 'home', label: '工作台', icon: 'home', path: '/mobile/home' },
  { key: 'assets', label: '资产', icon: 'box', path: '/mobile/assets' },
  { key: 'inventory', label: '盘点', icon: 'scan', path: '/mobile/inventory' },
  { key: 'approval', label: '审批', icon: 'check', path: '/mobile/approval' },
  { key: 'profile', label: '我的', icon: 'user', path: '/mobile/profile' },
]

function navigateTo(path: string) {
  router.push(path)
}

function getTabIcon(name: string): string {
  const icons: Record<string, string> = {
    home: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>`,
    box: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>`,
    scan: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><line x1="7" y1="12" x2="17" y2="12"/></svg>`,
    check: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4.5 4.5"/></svg>`,
    user: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
  }
  return icons[name] || icons.home
}
</script>

<template>
  <div class="mobile-layout">
    <main class="mobile-content">
      <router-view />
    </main>

    <nav class="mobile-tabbar">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-item"
        :class="{ active: activeTab === tab.key }"
        @click="navigateTo(tab.path)"
      >
        <span class="tab-icon" v-html="getTabIcon(tab.icon)" />
        <span class="tab-label">{{ tab.label }}</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.mobile-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-page);
  max-width: 480px;
  margin: 0 auto;
}

.mobile-content {
  flex: 1;
  padding-bottom: 64px;
  overflow-y: auto;
}

.mobile-tabbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 64px;
  background: var(--color-bg-card);
  border-top: 1px solid var(--color-border);
  display: flex;
  max-width: 480px;
  margin: 0 auto;
}

.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: none;
  border: none;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: color 0.2s;
}

.tab-item.active {
  color: var(--color-primary-500);
}

.tab-icon {
  width: 24px;
  height: 24px;
}

.tab-icon :deep(svg) {
  width: 100%;
  height: 100%;
}

.tab-label {
  font-size: 11px;
}
</style>
