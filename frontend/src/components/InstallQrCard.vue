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
@media (max-width: 768px) { .install-qr-card { display: none; } }
.install-qr-card { position: fixed; right: 20px; bottom: 20px; z-index: 100; display: flex; align-items: center; gap: 16px; padding: 14px 18px; background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 14px; box-shadow: 0 8px 24px rgba(0,0,0,.12); }
.qr-info h3 { margin: 0 0 6px; font-size: 16px; color: var(--color-text-primary); }
.qr-info p { margin: 0 0 4px; font-size: 14px; color: var(--color-text-secondary); }
.qr-hint { font-size: 12px; color: var(--color-text-tertiary); }
.qr-box { margin-left: auto; text-align: center; }
.qr-box canvas { display: block; background: #fff; border: 1px solid var(--color-border); border-radius: 8px; }
.qr-url { margin: 6px 0 0; font-size: 11px; color: var(--color-text-tertiary); font-family: var(--font-mono, monospace); }
</style>
