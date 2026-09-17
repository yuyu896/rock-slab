<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const ua = navigator.userAgent
const isWechat = /MicroMessenger/i.test(ua)
const isIos = /iphone|ipad|ipod/i.test(ua)
const isAndroid = /android/i.test(ua)
const isDesktop = !isIos && !isAndroid && !isWechat

const installPromptEvent = ref<any>(null)
const showInstallBtn = ref(false)

onMounted(() => {
  // 仅安卓非微信环境监听安装横幅事件；未触发则保持菜单图文兜底（厂商浏览器）
  if (isAndroid && !isWechat) {
    window.addEventListener('beforeinstallprompt', (e: Event) => {
      e.preventDefault()
      installPromptEvent.value = e
      showInstallBtn.value = true
    }, { once: true })
  }
})

async function doInstall() {
  if (!installPromptEvent.value) return
  installPromptEvent.value.prompt()
  await installPromptEvent.value.userChoice.catch(() => null)
}

function openApp() {
  router.push('/mobile/scan')
}
</script>

<template>
  <div class="install-guide">
    <div class="guide-head">
      <svg class="logo" viewBox="0 0 48 48">
        <rect x="8" y="30" width="32" height="11" rx="2.5" fill="#7aa6e8" />
        <rect x="8" y="18.5" width="32" height="11" rx="2.5" fill="#3b6fd4" />
        <rect x="8" y="7" width="32" height="11" rx="2.5" fill="#3457b8" />
        <path d="M20 12.5l2.8 2.8L28 10" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" fill="none" />
      </svg>
      <h1>磐盘</h1>
      <p>资产盘点 · 扫码查询</p>
    </div>

    <div class="guide-steps">
      <div v-if="isWechat" class="step-card">
        <h3>当前在微信内，先跳到浏览器</h3>
        <ol>
          <li>点右上角 <b>···</b></li>
          <li>选择「<b>在浏览器打开</b>」</li>
        </ol>
        <p class="tip">跳出去之后，按新页面提示继续安装</p>
      </div>

      <div v-else-if="isIos" class="step-card">
        <h3>iPhone 安装（三步）</h3>
        <ol>
          <li>点浏览器底部的 <b>分享</b> 按钮（向上箭头出方框）</li>
          <li>往下滚动，点「<b>添加到主屏幕</b>」</li>
          <li>点右上角「<b>添加</b>」</li>
        </ol>
      </div>

      <div v-else-if="isDesktop" class="step-card">
        <h3>请在手机上打开本页</h3>
        <p>用手机扫描 PC 工作台上的二维码，即可按提示安装移动端。</p>
      </div>

      <template v-else>
        <div v-if="showInstallBtn" class="step-card">
          <button class="install-big-btn" @click="doInstall">安装磐盘</button>
          <p class="tip">点击后按系统弹窗确认安装</p>
        </div>
        <div v-else class="step-card">
          <h3>安卓安装（两步）</h3>
          <ol>
            <li>点浏览器菜单 <b>⋮</b>（右上角三个点）</li>
            <li>点「<b>添加到主屏幕</b> / 安装应用」</li>
          </ol>
        </div>
      </template>
    </div>

    <button class="open-btn" @click="openApp">打开磐盘 →</button>
    <p class="already">已安装？直接打开使用</p>
  </div>
</template>

<style scoped>
.install-guide { min-height: 100vh; max-width: 480px; margin: 0 auto; padding: 48px 24px 32px; display: flex; flex-direction: column; align-items: center; background: var(--color-bg-page); }
.guide-head { text-align: center; margin-bottom: 28px; }
.logo { width: 72px; height: 72px; }
.guide-head h1 { margin: 12px 0 4px; font-size: 24px; color: var(--color-text-primary); }
.guide-head p { margin: 0; font-size: 14px; color: var(--color-text-secondary); }
.guide-steps { width: 100%; }
.step-card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 14px; padding: 20px; }
.step-card h3 { margin: 0 0 12px; font-size: 16px; color: var(--color-text-primary); }
.step-card ol { margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 8px; font-size: 15px; color: var(--color-text-primary); }
.step-card .tip { margin: 12px 0 0; font-size: 13px; color: var(--color-text-tertiary); }
.install-big-btn { width: 100%; padding: 14px; border: none; border-radius: 12px; background: var(--color-primary-500); color: #fff; font-size: 17px; cursor: pointer; }
.open-btn { margin-top: 28px; width: 100%; padding: 12px; border: 1px solid var(--color-primary-500); border-radius: 12px; background: transparent; color: var(--color-primary-500); font-size: 15px; cursor: pointer; }
.already { margin-top: 8px; font-size: 12px; color: var(--color-text-tertiary); text-align: center; }
</style>
