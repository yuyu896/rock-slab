<script setup lang="ts">
import { onMounted, ref } from 'vue'
import QRCode from 'qrcode'

/** 移动端盘点入口二维码：内容 = 当前域名/mobile/inventory，本地/生产自适应（组件沿用旧名，语义已从安装引导变为盘点入口） */
const canvasRef = ref<HTMLCanvasElement | null>(null)
const inventoryUrl = `${location.origin}/mobile/inventory`

onMounted(async () => {
  if (!canvasRef.value) return
  try {
    await QRCode.toCanvas(canvasRef.value, inventoryUrl, {
      width: 144,
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
    <h3>移动端盘点</h3>
    <div class="qr-box">
      <canvas ref="canvasRef" width="144" height="144"></canvas>
    </div>
  </div>
</template>

<style scoped>
.install-qr-card { display: flex; flex-direction: column; align-items: center; gap: 8px; width: 160px; }
.install-qr-card h3 { margin: 0; font-size: 13px; color: var(--color-text-secondary); font-weight: 500; }
.qr-box { width: 144px; height: 144px; background: white; border: 1px solid var(--color-border); border-radius: 8px; }
.qr-box canvas { display: block; width: 144px; height: 144px; }
</style>
