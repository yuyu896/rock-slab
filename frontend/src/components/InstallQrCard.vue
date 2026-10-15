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
      width: 88,
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
    <div class="qr-heading">
      <h3>移动端盘点</h3>
    </div>
    <div class="qr-content">
      <div class="qr-info">
        <p>微信扫码使用移动端进行盘点</p>
        <p class="qr-hint">首次使用需登录，登录后选择盘点任务</p>
      </div>
      <div class="qr-box">
        <canvas ref="canvasRef" width="88" height="88"></canvas>
      </div>
    </div>
  </div>
</template>

<style scoped>
.install-qr-card { display: flex; flex-direction: column; align-items: center; gap: 8px; width: 200px; }
.qr-heading { width: 200px; min-height: 24px; display: flex; align-items: center; justify-content: center; }
.qr-heading h3 { margin: 0; font-size: 13px; color: var(--color-text-secondary); font-weight: 500; }
.qr-content { width: 200px; display: flex; align-items: center; gap: var(--space-3); }
.qr-info { flex: 1; min-width: 0; text-align: left; }
.qr-info p { margin: 0 0 2px; font-size: 11px; line-height: 1.4; color: var(--color-text-tertiary); }
.qr-info .qr-hint { font-size: 10px; }
.qr-box { width: 88px; height: 88px; background: white; border: 1px solid var(--color-border); border-radius: 8px; }
.qr-box canvas { display: block; width: 88px; height: 88px; }
</style>
