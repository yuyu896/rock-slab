<script setup lang="ts">
import { onMounted, ref } from 'vue'
import QRCode from 'qrcode'

/** 移动端盘点入口二维码：内容 = 当前域名/mobile/inventory，本地/生产自适应（组件沿用旧名，语义已从安装引导变为盘点入口） */
const canvasRef = ref<HTMLCanvasElement | null>(null)
const entryUrl = `${location.origin}/mobile/inventory`

onMounted(async () => {
  if (!canvasRef.value) return
  try {
    await QRCode.toCanvas(canvasRef.value, `${location.origin}/mobile/inventory`, {
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
      <h3>移动端盘点</h3>
      <p>微信扫码使用移动端进行盘点</p>
      <p class="qr-hint">首次使用需登录，登录后选择盘点任务</p>
    </div>
    <div class="qr-box">
      <canvas ref="canvasRef" width="128" height="128"></canvas>
      <p class="qr-url">{{ entryUrl }}</p>
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
