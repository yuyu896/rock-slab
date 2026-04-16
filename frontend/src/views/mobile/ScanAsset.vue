<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { getAssets } from '@/api/assets'
import { ElMessage } from 'element-plus'
import type { Asset } from '@/types'

const router = useRouter()
const scanInput = ref('')
const scannedAsset = ref<Asset | null>(null)
const loading = ref(false)
const showResult = ref(false)

// 摄像头扫码相关
const showCamera = ref(false)
const videoRef = ref<HTMLVideoElement | null>(null)
const cameraStream = ref<MediaStream | null>(null)
const barcodeDetectorSupported = ref(false)
let scanInterval: ReturnType<typeof setInterval> | null = null

// 检测 BarcodeDetector 支持
if ('BarcodeDetector' in window) {
  barcodeDetectorSupported.value = true
}

function toggleCamera() {
  if (showCamera.value) {
    stopCamera()
  } else {
    startCamera()
  }
}

async function startCamera() {
  if (!barcodeDetectorSupported.value) {
    ElMessage.warning('当前浏览器不支持摄像头扫码，请使用手动输入')
    return
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment' }
    })
    cameraStream.value = stream
    showCamera.value = true
    setTimeout(() => {
      if (videoRef.value) {
        videoRef.value.srcObject = stream
        videoRef.value.play()
        startBarcodeDetection()
      }
    }, 100)
  } catch (error) {
    ElMessage.error('无法访问摄像头，请检查权限设置')
  }
}

function stopCamera() {
  showCamera.value = false
  if (scanInterval) {
    clearInterval(scanInterval)
    scanInterval = null
  }
  if (cameraStream.value) {
    cameraStream.value.getTracks().forEach(track => track.stop())
    cameraStream.value = null
  }
  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
}

function startBarcodeDetection() {
  if (!barcodeDetectorSupported.value) return
  const detector = new (window as any).BarcodeDetector({ formats: ['qr_code', 'ean_13', 'ean_8', 'code_128', 'code_39'] })
  scanInterval = setInterval(async () => {
    if (!videoRef.value || !showCamera.value) return
    try {
      const barcodes = await detector.detect(videoRef.value)
      if (barcodes.length > 0) {
        const code = barcodes[0].rawValue
        if (code) {
          scanInput.value = code
          stopCamera()
          handleScan()
        }
      }
    } catch {
      // detection can fail on some frames, ignore
    }
  }, 500)
}

// 监听扫码输入
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && scanInput.value.trim()) {
    handleScan()
  }
}

async function handleScan() {
  if (!scanInput.value.trim()) {
    ElMessage.warning('请输入或扫描资产编号')
    return
  }

  loading.value = true
  showResult.value = false

  try {
    const { data } = await getAssets({
      keyword: scanInput.value.trim(),
      pageSize: 1,
    })
    if (data.results && data.results.length > 0) {
      scannedAsset.value = data.results[0]
      showResult.value = true
    } else {
      ElMessage.warning('未找到对应资产')
      scannedAsset.value = null
    }
  } catch (error) {
    ElMessage.error('查询失败')
  } finally {
    loading.value = false
  }
}

function viewDetail() {
  if (scannedAsset.value) {
    router.push(`/mobile/assets/${scannedAsset.value.id}`)
  }
}

function clearScan() {
  scanInput.value = ''
  scannedAsset.value = null
  showResult.value = false
}

onMounted(() => {
  // 自动聚焦到输入框
  const input = document.querySelector('.scan-input') as HTMLInputElement
  if (input) {
    input.focus()
  }
})

onUnmounted(() => {
  stopCamera()
})
</script>

<template>
  <div class="scan-asset-page">
    <!-- 头部 -->
    <div class="page-header">
      <h1>扫码查询</h1>
    </div>

    <!-- 扫码输入区 -->
    <div class="scan-section">
      <div class="scan-input-wrapper">
        <svg class="scan-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/>
          <line x1="7" y1="12" x2="17" y2="12"/>
        </svg>
        <input
          v-model="scanInput"
          type="text"
          class="scan-input"
          placeholder="请扫描或输入资产编号"
          @keydown="handleKeydown"
        />
      </div>
      <button class="scan-btn" @click="handleScan">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="M21 21l-4.35-4.35"/>
        </svg>
        <span>查询</span>
      </button>
      <button class="camera-btn" @click="toggleCamera" :class="{ active: showCamera }">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
          <circle cx="12" cy="13" r="4"/>
        </svg>
        <span>摄像头扫码</span>
      </button>
    </div>

    <!-- 摄像头视图 -->
    <div v-if="showCamera" class="camera-view">
      <video ref="videoRef" class="camera-video" playsinline muted></video>
      <div class="camera-overlay">
        <div class="scan-frame"></div>
      </div>
      <button class="camera-close-btn" @click="stopCamera">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>
    <p v-if="!barcodeDetectorSupported && showCamera" class="camera-hint">当前浏览器不支持摄像头扫码，请使用手动输入</p>

    <!-- 扫描结果 -->
    <div v-if="showResult && scannedAsset" class="result-section">
      <div class="result-card" @click="viewDetail">
        <div class="asset-header">
          <span class="asset-status" :class="scannedAsset.当前状态">
            {{ scannedAsset.当前状态 }}
          </span>
        </div>
        <div class="asset-image">
          <img v-if="scannedAsset.图片" :src="scannedAsset.图片" />
          <div v-else class="asset-placeholder">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
            </svg>
          </div>
        </div>
        <div class="asset-info">
          <div class="asset-code">{{ scannedAsset.资产编号 }}</div>
          <div class="asset-name">{{ scannedAsset.资产名称 }}</div>
          <div class="asset-meta">
            <div class="meta-item">
              <span class="label">分公司</span>
              <span class="value">{{ scannedAsset.分公司 }}</span>
            </div>
            <div class="meta-item">
              <span class="label">规格型号</span>
              <span class="value">{{ scannedAsset.规格 || '-' }}</span>
            </div>
            <div class="meta-item">
              <span class="label">数量</span>
              <span class="value">{{ scannedAsset.数量 }}</span>
            </div>
          </div>
        </div>

        <div class="result-actions">
          <button class="detail-btn" @click="viewDetail">
            查看详情
          </button>
          <button class="clear-btn" @click="clearScan">
            继续扫码
          </button>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay">
      <span>查询中...</span>
    </div>
  </div>
</template>

<style scoped>
.scan-asset-page {
  padding: var(--space-4);
  min-height: 100vh;
}

.page-header {
  margin-bottom: var(--space-4);
}

.page-header h1 {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.scan-section {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.scan-input-wrapper {
  flex: 1;
  position: relative;
}

.scan-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 20px;
  height: 20px;
  color: var(--color-text-tertiary);
}

.scan-input {
  width: 100%;
  height: 50px;
  padding: 0 var(--space-4) 0 44px;
  border: 2px dashed var(--color-border);
  border-radius: 12px;
  background: var(--color-bg-card);
  font-size: 16px;
  text-align: center;
}

.scan-input:focus {
  outline: none;
  border-color: var(--color-primary-500);
}

.scan-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 70px;
  height: 50px;
  border: none;
  border-radius: 12px;
  background: var(--color-primary-500);
  color: white;
  cursor: pointer;
}

.scan-btn svg {
  width: 22px;
  height: 22px;
}

.scan-btn span {
  font-size: 11px;
}

.camera-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 100%;
  height: 44px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-bg-card);
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: 13px;
  margin-top: var(--space-2);
}

.camera-btn svg {
  width: 18px;
  height: 18px;
}

.camera-btn.active {
  border-color: var(--color-primary-500);
  color: var(--color-primary-500);
  background: var(--color-primary-50);
}

.camera-view {
  position: relative;
  width: 100%;
  height: 240px;
  border-radius: 12px;
  overflow: hidden;
  background: #000;
  margin-bottom: var(--space-3);
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.camera-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
}

.scan-frame {
  width: 200px;
  height: 120px;
  border: 2px solid rgba(255, 255, 255, 0.8);
  border-radius: 8px;
}

.camera-close-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  border: none;
  border-radius: 50%;
  color: white;
  cursor: pointer;
}

.camera-close-btn svg {
  width: 16px;
  height: 16px;
}

.camera-hint {
  font-size: 13px;
  color: var(--color-warning);
  text-align: center;
  margin-bottom: var(--space-3);
}

.result-section {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.result-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
}

.asset-header {
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-elevated);
  display: flex;
  justify-content: flex-end;
}

.asset-status {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.asset-status.在库 {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.asset-status.使用中 {
  background: var(--color-primary-50);
  color: var(--color-primary-500);
}

.asset-status.维修中 {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.asset-status.报废 {
  background: var(--color-danger-bg);
  color: var(--color-danger);
}

.asset-image {
  width: 100%;
  height: 180px;
  background: var(--color-bg-page);
  display: flex;
  align-items: center;
  justify-content: center;
}

.asset-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.asset-placeholder {
  width: 64px;
  height: 64px;
  color: var(--color-text-tertiary);
}

.asset-placeholder svg {
  width: 100%;
  height: 100%;
}

.asset-info {
  padding: var(--space-4);
}

.asset-code {
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--color-text-tertiary);
}

.asset-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-top: 4px;
}

.asset-meta {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
  margin-top: var(--space-3);
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.meta-item .label {
  font-size: 11px;
  color: var(--color-text-tertiary);
}

.meta-item .value {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
}

.result-actions {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.detail-btn,
.clear-btn {
  flex: 1;
  height: 44px;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
}

.detail-btn {
  background: var(--color-primary-500);
  color: white;
}

.clear-btn {
  background: var(--color-bg-elevated);
  color: var(--color-text-secondary);
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  color: var(--color-text-secondary);
}
</style>
