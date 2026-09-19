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
      width: 128,
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
      <canvas ref="canvasRef" width="128" height="128"></canvas>
      <p class="qr-url">{{ installUrl }}</p>
    </div>
  </div>
</template>

<style scoped>
.install-qr-card { display: flex; align-items: center; gap: 10px; padding: 0; background: transparent; border: none; box-shadow: none; }
.qr-info h3 { margin: 0 0 2px; font-size: 12px; color: var(--color-text-secondary); font-weight: 500; }
.qr-info p { margin: 0 0 2px; font-size: 12px; color: var(--color-text-tertiary); }
.qr-hint { font-size: 10px; color: var(--color-text-tertiary); }
.qr-box { margin-left: 0; text-align: center; }
.qr-box canvas { display: block; background: #fff; border-radius: 8px; }
.qr-url { margin: 4px 0 0; font-size: 10px; color: var(--color-text-tertiary); font-family: var(--font-mono, monospace); }
</style>
