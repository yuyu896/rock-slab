<script setup lang="ts">
import { onMounted, ref } from 'vue'
import QRCode from 'qrcode'

/** 二维码运行时生成：内容 = 当前域名/install，本地/生产自适应 */
const canvasRef = ref<HTMLCanvasElement | null>(null)
const installUrl = `${location.origin}/install`

onMounted(async () => {
  if (!canvasRef.value) return
  try {
    await QRCode.toCanvas(canvasRef.value, `${location.origin}/install`, {
      width: 160,
      margin: 2,
      errorCorrectionLevel: 'M',
    })
  } catch {
    // 二维码生成失败时保留占位
  }
})
</script>

<template>
  <div class="install-qr-card">
    <div class="qr-info">
      <h3>移动端安装</h3>
      <p>手机扫码，安装磐盘移动端</p>
      <p class="qr-hint">安卓两下 · iPhone 四下，装完桌面有图标</p>
    </div>
    <div class="qr-box">
      <canvas ref="canvasRef" width="160" height="160"></canvas>
      <p class="qr-url">{{ installUrl }}</p>
    </div>
  </div>
</template>

<style scoped>
.install-qr-card { display: flex; align-items: center; gap: 24px; padding: 20px 24px; background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 14px; }
.qr-info h3 { margin: 0 0 6px; font-size: 16px; color: var(--color-text-primary); }
.qr-info p { margin: 0 0 4px; font-size: 14px; color: var(--color-text-secondary); }
.qr-hint { font-size: 12px; color: var(--color-text-tertiary); }
.qr-box { margin-left: auto; text-align: center; }
.qr-box canvas { display: block; background: #fff; border: 1px solid var(--color-border); border-radius: 8px; }
.qr-url { margin: 6px 0 0; font-size: 11px; color: var(--color-text-tertiary); font-family: var(--font-mono, monospace); }
</style>
