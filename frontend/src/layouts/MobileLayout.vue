<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// ── PWA 安装引导：安卓 Chrome 捕获 beforeinstallprompt 出一键安装；iOS 给菜单引导 ──
const installPrompt = ref<any>(null)
const showInstallBanner = ref(false)
const dismissed = () => sessionStorage.getItem('rock_slab_pwa_hint_dismissed') === '1'
const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent)

onMounted(() => {
  window.addEventListener('beforeinstallprompt', (e: Event) => {
    e.preventDefault()
    installPrompt.value = e
    if (!dismissed()) showInstallBanner.value = true
  })
  // iOS 无 beforeinstallprompt：直接展示引导文案
  if (isIos && !dismissed()) showInstallBanner.value = true
})

async function doInstall() {
  if (!installPrompt.value) return
  installPrompt.value.prompt()
  await installPrompt.value.userChoice.catch(() => null)
  showInstallBanner.value = false
}

function dismissBanner() {
  showInstallBanner.value = false
  sessionStorage.setItem('rock_slab_pwa_hint_dismissed', '1')
}

const activeTab = computed(() => {
  const path = route.path
  if (path.includes('/mobile/scan')) return 'scan'
  if (path.includes('/mobile/inventory')) return 'inventory'
  if (path.includes('/mobile/profile')) return 'profile'
  return 'scan'
})

/* 移动端定位为扫码终端：只保留 扫码/盘点任务/我的（PC 端功能不受影响） */
const tabs = [
  { key: 'scan', label: '扫码', icon: 'scan', path: '/mobile/scan' },
  { key: 'inventory', label: '盘点任务', icon: 'box', path: '/mobile/inventory' },
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
    <div v-if="showInstallBanner" class="install-banner">
      <span class="install-text">
        {{ installPrompt ? '把磐盘安装到桌面，一点即用' : 'iOS：Safari 分享 → 添加到主屏幕' }}
      </span>
      <button v-if="installPrompt" class="install-btn" @click="doInstall">安装</button>
      <button class="install-close" @click="dismissBanner">&times;</button>
    </div>

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
.install-banner { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: var(--color-primary-50, #eef4ee); border-bottom: 1px solid var(--color-border); font-size: 13px; color: var(--color-text-primary); }
.install-text { flex: 1; }
.install-btn { padding: 5px 14px; border: none; border-radius: 6px; background: var(--color-primary-500); color: #fff; font-size: 13px; cursor: pointer; }
.install-close { background: none; border: none; font-size: 20px; color: var(--color-text-tertiary); cursor: pointer; line-height: 1; }

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
