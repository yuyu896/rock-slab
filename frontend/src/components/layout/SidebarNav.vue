<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

interface NavItem {
  icon: string
  label: string
  path: string
  badge?: number
  children?: NavItem[]
}

defineProps<{
  isCollapsed: boolean
}>()

const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => route.path)
const expandedMenu = ref<string | null>(null)

const navItems: NavItem[] = [
  {
    icon: 'dashboard',
    label: '工作台',
    path: '/dashboard'
  },
  {
    icon: 'chart',
    label: '统计报表',
    path: '/reports'
  },
  {
    icon: 'category',
    label: '资产分类',
    path: '/categories'
  },
  {
    icon: 'box',
    label: '资产列表',
    path: '/assets/list'
  },
  {
    icon: 'transfer',
    label: '资产流转',
    path: '/transfers',
    children: [
      { icon: '', label: '采购入库', path: '/assets/purchase' },
      { icon: '', label: '领用出库', path: '/transfers/assign' },
      { icon: '', label: '调拨', path: '/transfers/transfer' },
    ]
  },
  {
    icon: 'scan',
    label: '资产盘点',
    path: '/inventory',
    badge: 3
  },
  {
    icon: 'organization',
    label: '组织架构',
    path: '/organization'
  }
]

const navigateTo = (path: string) => {
  router.push(path)
}

const isActive = (path: string) => {
  return activeMenu.value === path || activeMenu.value.startsWith(path + '/')
}

const isChildActive = (item: NavItem) => {
  if (!item.children) return false
  return item.children.some(child => activeMenu.value === child.path || activeMenu.value.startsWith(child.path + '/'))
}

const toggleDropdown = (path: string) => {
  expandedMenu.value = expandedMenu.value === path ? null : path
}

const getIcon = (name: string) => {
  const icons: Record<string, string> = {
    dashboard: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>`,
    category: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h16"/></svg>`,
    box: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>`,
    scan: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><line x1="7" y1="12" x2="17" y2="12"/></svg>`,
    organization: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
    chart: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>`,
    transfer: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>`
  }
  return icons[name] || icons.dashboard
}
</script>

<template>
  <nav class="sidebar-nav">
    <ul class="nav-list">
      <li v-for="item in navItems" :key="item.path" class="nav-item">
        <a
          v-if="!item.children"
          class="nav-link"
          :class="{ active: isActive(item.path) }"
          @click="navigateTo(item.path)"
        >
          <span class="nav-icon" v-html="getIcon(item.icon)" />
          <transition name="fade">
            <span v-if="!isCollapsed" class="nav-label">{{ item.label }}</span>
          </transition>
          <span v-if="item.badge && !isCollapsed" class="nav-badge">{{ item.badge }}</span>
        </a>

        <template v-else>
          <a class="nav-link" :class="{ active: isActive(item.path) || isChildActive(item) }" @click.stop="toggleDropdown(item.path)">
            <span class="nav-icon" v-html="getIcon(item.icon)" />
            <transition name="fade">
              <span v-if="!isCollapsed" class="nav-label">{{ item.label }}</span>
            </transition>
            <svg v-if="!isCollapsed" class="nav-arrow" :class="{ rotated: expandedMenu === item.path }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18l6-6-6-6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </a>
          <div v-if="!isCollapsed" class="nav-submenu" :class="{ expanded: expandedMenu === item.path }">
            <a
              v-for="child in item.children"
              :key="child.path"
              class="nav-submenu-item"
              :class="{ active: isActive(child.path) }"
              @click="navigateTo(child.path)"
            >
              {{ child.label }}
            </a>
          </div>
        </template>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.sidebar-nav {
  flex: 1;
  padding: var(--space-4) var(--space-3);
  overflow-y: auto;
}

.nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.nav-item {
  margin-bottom: var(--space-1);
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-3);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 1);
}

.nav-link:focus-visible {
  outline: 2px solid var(--color-primary-300);
  outline-offset: 2px;
}

.nav-link.active {
  background: rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 1);
}

.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-icon :deep(svg) {
  width: 100%;
  height: 100%;
}

.nav-label {
  flex: 1;
  font-size: var(--text-sm);
  font-weight: 500;
  white-space: nowrap;
}

.nav-badge {
  background: var(--color-danger);
  color: white;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}

.nav-arrow {
  width: 16px;
  height: 16px;
  margin-left: auto;
  transition: transform var(--transition-fast);
}

.nav-arrow.rotated {
  transform: rotate(90deg);
}

/* 内联折叠子菜单 */
.nav-submenu {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.2s ease;
}

.nav-submenu.expanded {
  max-height: 400px;
}

.nav-submenu-item {
  display: block;
  padding: var(--space-2) var(--space-3) var(--space-2) var(--space-10);
  font-size: var(--text-sm);
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.nav-submenu-item:hover {
  color: rgba(255, 255, 255, 1);
  background: rgba(255, 255, 255, 0.1);
}

.nav-submenu-item.active {
  color: rgba(255, 255, 255, 1);
  background: rgba(255, 255, 255, 0.15);
  font-weight: 500;
}

@media (max-width: 768px) {
  .nav-link {
    min-height: 44px;
    padding: var(--space-3) var(--space-4);
  }
}
</style>
