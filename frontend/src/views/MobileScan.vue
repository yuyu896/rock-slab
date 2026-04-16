<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getInventoryTask, getInventoryProgress, checkInventoryItem, getInventoryChecks, submitInventory } from '@/api/inventories'
import { getAssets } from '@/api/assets'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import type { Asset } from '@/types'

const route = useRoute()
const router = useRouter()
const taskId = route.params.taskId as string

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
    // 等待视频元素渲染后设置 srcObject
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

// 任务信息
const taskInfo = ref<{
  id: string
  name: string
  branch: string
  totalItems: number
  checkedItems: number
  surplusCount: number
  missingCount: number
}>({
  id: taskId,
  name: '',
  branch: '',
  totalItems: 0,
  checkedItems: 0,
  surplusCount: 0,
  missingCount: 0
})

// 扫码输入
const scanInput = ref('')
const isScanning = ref(false)

// 最近扫描记录
const recentScans = ref<any[]>([])

// 弹窗状态
const showResultModal = ref(false)
const currentScanResult = ref<{ assetId: string; code: string; name: string; expected: number; actual: number | null; result: string } | null>(null)
const actualQty = ref(1)

// 进度计算
const progress = computed(() => {
  if (taskInfo.value.totalItems === 0) return 0
  return Math.round(taskInfo.value.checkedItems / taskInfo.value.totalItems * 100)
})

// 获取任务详情和进度
async function fetchTaskData() {
  try {
    const [taskRes, progressRes] = await Promise.all([
      getInventoryTask(taskId),
      getInventoryProgress(taskId)
    ])
    taskInfo.value = {
      id: taskId,
      name: taskRes.data.name,
      branch: taskRes.data.branchId || '',
      totalItems: progressRes.data.totalItems,
      checkedItems: progressRes.data.checkedItems,
      surplusCount: progressRes.data.surplusCount,
      missingCount: progressRes.data.missingCount
    }
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 获取最近盘点记录
async function fetchRecentChecks() {
  try {
    const { data } = await getInventoryChecks(taskId, { pageSize: 10 })
    recentScans.value = data.results
  } catch (error) {
    console.error('Failed to fetch checks:', error)
  }
}

// 扫码处理 — 查找资产并弹出确认
const handleScan = async () => {
  if (!scanInput.value.trim()) return

  isScanning.value = true
  try {
    const { data } = await getAssets({ keyword: scanInput.value.trim(), pageSize: 1 })
    const results = data.results || data as any
    const assets = Array.isArray(results) ? results : []
    if (assets.length === 0) {
      ElMessage.warning('未找到该资产')
      isScanning.value = false
      return
    }
    const asset: Asset = assets[0]
    currentScanResult.value = {
      assetId: asset.id,
      code: asset.资产编号,
      name: asset.资产名称,
      expected: asset.数量,
      actual: null,
      result: 'pending'
    }
    actualQty.value = asset.数量
    showResultModal.value = true
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    isScanning.value = false
  }
}

// 确认盘点结果
const confirmScan = async () => {
  if (!currentScanResult.value) return

  try {
    await checkInventoryItem(taskId, {
      assetId: currentScanResult.value.assetId,
      qty: actualQty.value
    })

    showResultModal.value = false
    scanInput.value = ''
    ElMessage.success('盘点完成')
    // 刷新数据
    await Promise.all([fetchTaskData(), fetchRecentChecks()])
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 获取结果样式
const getResultStyle = (result: string) => {
  const styles: Record<string, { bg: string; color: string; icon: string }> = {
    'matched': { bg: 'oklch(0.92 0.08 145)', color: 'var(--color-success)', icon: '✓' },
    'surplus': { bg: 'oklch(0.94 0.06 85)', color: 'oklch(0.55 0.14 85)', icon: '↑' },
    'missing': { bg: 'oklch(0.92 0.10 25)', color: 'var(--color-danger)', icon: '↓' }
  }
  return styles[result] || styles['matched']
}

// 完成盘点
const finishInventory = async () => {
  try {
    await submitInventory(taskId)
    ElMessage.success('盘点已提交审核')
    router.back()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 暂停盘点
const pauseInventory = () => {
  router.back()
}

// 关闭页面
const closePage = () => {
  router.back()
}

// 键盘事件处理（监听扫码枪输入）
const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && scanInput.value) {
    handleScan()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  fetchTaskData()
  fetchRecentChecks()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  stopCamera()
})
</script>

<template>
  <div class="mobile-scan-page">
    <!-- 顶部状态栏 -->
    <div class="status-bar">
      <div class="task-info">
        <h2 class="task-name">{{ taskInfo.name }}</h2>
        <span class="task-branch">{{ taskInfo.branch }}</span>
      </div>
      <button class="close-btn" @click="closePage">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>

    <!-- 进度卡片 -->
    <div class="progress-card">
      <div class="progress-ring">
        <svg viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="42"
            fill="none"
            stroke="var(--color-bg-elevated)"
            stroke-width="8"
          />
          <circle
            cx="50"
            cy="50"
            r="42"
            fill="none"
            stroke="var(--color-primary-500)"
            stroke-width="8"
            stroke-linecap="round"
            :stroke-dasharray="264"
            :stroke-dashoffset="264 * (1 - progress / 100)"
            transform="rotate(-90 50 50)"
          />
        </svg>
        <div class="progress-center">
          <span class="progress-value">{{ progress }}%</span>
        </div>
      </div>
      <div class="progress-stats">
        <div class="progress-stat">
          <span class="stat-value">{{ taskInfo.checkedItems }}</span>
          <span class="stat-label">已盘点</span>
        </div>
        <div class="progress-stat">
          <span class="stat-value">{{ taskInfo.totalItems - taskInfo.checkedItems }}</span>
          <span class="stat-label">未盘点</span>
        </div>
      </div>
    </div>

    <!-- 扫码区域 -->
    <div class="scan-section">
      <div class="scan-input-wrapper">
        <div class="scan-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/>
            <line x1="7" y1="12" x2="17" y2="12"/>
          </svg>
        </div>
        <input
          ref="scanInputRef"
          v-model="scanInput"
          type="text"
          placeholder="扫描或输入资产编号..."
          class="scan-input"
          @keyup.enter="handleScan"
        />
        <button class="scan-btn" @click="handleScan" :disabled="isScanning">
          <svg v-if="!isScanning" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="M21 21l-4.35-4.35"/>
          </svg>
          <svg v-else class="spinning" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 6v6l4 2"/>
          </svg>
        </button>
        <button class="camera-toggle-btn" @click="toggleCamera" :class="{ active: showCamera }">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
            <circle cx="12" cy="13" r="4"/>
          </svg>
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
      <p class="scan-hint">支持扫码枪直接扫描，或手动输入编号后点击搜索</p>
      <p v-if="!barcodeDetectorSupported" class="scan-hint camera-not-supported">当前浏览器不支持摄像头扫码，请使用手动输入</p>
    </div>

    <!-- 异常统计 -->
    <div class="abnormal-stats">
      <div class="abnormal-item surplus">
        <span class="abnormal-icon">↑</span>
        <div class="abnormal-content">
          <span class="abnormal-value">{{ taskInfo.surplusCount }}</span>
          <span class="abnormal-label">盘盈</span>
        </div>
      </div>
      <div class="abnormal-item missing">
        <span class="abnormal-icon">↓</span>
        <div class="abnormal-content">
          <span class="abnormal-value">{{ taskInfo.missingCount }}</span>
          <span class="abnormal-label">盘亏</span>
        </div>
      </div>
    </div>

    <!-- 最近扫描记录 -->
    <div class="recent-section">
      <div class="section-header">
        <h3 class="section-title">最近扫描</h3>
        <span class="section-count">{{ recentScans.length }}条记录</span>
      </div>
      <div class="recent-list">
        <div
          v-for="scan in recentScans"
          :key="scan.id"
          class="recent-item"
          :class="scan.result"
        >
          <div class="recent-icon" :style="{ background: getResultStyle(scan.result).bg, color: getResultStyle(scan.result).color }">
            {{ getResultStyle(scan.result).icon }}
          </div>
          <div class="recent-content">
            <div class="recent-code">{{ scan.code }}</div>
            <div class="recent-name">{{ scan.name }}</div>
            <div class="recent-qty">
              账面: {{ scan.expected }} / 实际: {{ scan.actual }}
              <span v-if="scan.result === 'surplus'" class="qty-diff surplus">(+{{ scan.actual - scan.expected }})</span>
              <span v-if="scan.result === 'missing'" class="qty-diff missing">({{ scan.actual - scan.expected }})</span>
            </div>
          </div>
          <span class="recent-time">{{ scan.time }}</span>
        </div>
      </div>
    </div>

    <!-- 底部操作栏 -->
    <div class="bottom-bar">
      <button class="bottom-btn secondary" @click="pauseInventory">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
        暂停盘点
      </button>
      <button class="bottom-btn primary" @click="finishInventory">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
          <polyline points="22 4 12 14.01 9 11.01"/>
        </svg>
        完成盘点
      </button>
    </div>

    <!-- 盘点结果弹窗 -->
    <div v-if="showResultModal" class="modal-overlay">
      <div class="modal-content">
        <div class="modal-header">
          <h3 class="modal-title">确认盘点数量</h3>
        </div>

        <div class="modal-body">
          <div class="asset-info">
            <span class="asset-code">{{ currentScanResult?.code }}</span>
            <span class="asset-name">{{ currentScanResult?.name }}</span>
          </div>

          <div class="qty-section">
            <div class="qty-row">
              <span class="qty-label">账面数量</span>
              <span class="qty-value expected">{{ currentScanResult?.expected }}</span>
            </div>
            <div class="qty-divider">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19"/>
                <polyline points="19 12 12 19 5 12"/>
              </svg>
            </div>
            <div class="qty-row actual">
              <span class="qty-label">实际数量</span>
              <div class="qty-input-group">
                <button class="qty-btn minus" @click="actualQty = Math.max(0, actualQty - 1)">-</button>
                <input v-model="actualQty" type="number" class="qty-input" min="0" />
                <button class="qty-btn plus" @click="actualQty++">+</button>
              </div>
            </div>
          </div>

          <div v-if="currentScanResult && actualQty !== currentScanResult.expected" class="qty-alert" :class="{ surplus: actualQty > currentScanResult.expected, missing: actualQty < currentScanResult.expected }">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <span v-if="actualQty > currentScanResult.expected">盘盈 {{ actualQty - currentScanResult.expected }} 件</span>
            <span v-else>盘亏 {{ currentScanResult.expected - actualQty }} 件</span>
          </div>
        </div>

        <div class="modal-footer">
          <button class="modal-btn cancel" @click="showResultModal = false">取消</button>
          <button class="modal-btn confirm" @click="confirmScan">确认</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 移动端适配 */
.mobile-scan-page {
  min-height: 100vh;
  background: var(--color-bg-page);
  padding-bottom: 80px;
  max-width: 480px;
  margin: 0 auto;
}

/* 状态栏 */
.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 10;
}

.task-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.task-name {
  font-size: var(--text-base);
  font-weight: 600;
  margin: 0;
}

.task-branch {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.close-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-elevated);
  border: none;
  border-radius: 50%;
  color: var(--color-text-tertiary);
}

.close-btn svg {
  width: 20px;
  height: 20px;
}

/* 进度卡片 */
.progress-card {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  padding: var(--space-5);
  margin: var(--space-4);
  background: var(--color-bg-card);
  border-radius: 16px;
  border: 1px solid var(--color-border);
}

.progress-ring {
  width: 100px;
  height: 100px;
  position: relative;
  flex-shrink: 0;
}

.progress-ring svg {
  width: 100%;
  height: 100%;
}

.progress-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.progress-value {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-primary-600);
}

.progress-stats {
  display: flex;
  gap: var(--space-6);
}

.progress-stat {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.stat-label {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

/* 扫码区域 */
.scan-section {
  padding: var(--space-4);
}

.scan-input-wrapper {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: var(--color-bg-card);
  border: 2px solid var(--color-primary-300);
  border-radius: 12px;
  padding: var(--space-2);
}

.scan-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary-500);
}

.scan-icon svg {
  width: 24px;
  height: 24px;
}

.scan-input {
  flex: 1;
  height: 40px;
  border: none;
  background: transparent;
  font-size: var(--text-base);
  font-family: var(--font-mono);
}

.scan-input:focus {
  outline: none;
}

.scan-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-500);
  border: none;
  border-radius: 10px;
  color: white;
}

.scan-btn svg {
  width: 20px;
  height: 20px;
}

.scan-btn:disabled {
  opacity: 0.5;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.scan-hint {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  text-align: center;
  margin-top: var(--space-2);
}

.camera-not-supported {
  color: var(--color-warning);
}

.camera-toggle-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-elevated);
  border: none;
  border-radius: 10px;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.camera-toggle-btn svg {
  width: 20px;
  height: 20px;
}

.camera-toggle-btn.active {
  background: var(--color-primary-500);
  color: white;
}

.camera-view {
  position: relative;
  width: 100%;
  height: 240px;
  margin-top: var(--space-3);
  border-radius: 12px;
  overflow: hidden;
  background: #000;
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

/* 异常统计 */
.abnormal-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
  padding: 0 var(--space-4);
  margin-bottom: var(--space-4);
}

.abnormal-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
}

.abnormal-item.surplus {
  border-left: 4px solid var(--color-success);
}

.abnormal-item.missing {
  border-left: 4px solid var(--color-danger);
}

.abnormal-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-lg);
  font-weight: 700;
}

.abnormal-item.surplus .abnormal-icon {
  background: oklch(0.92 0.08 145);
  color: var(--color-success);
}

.abnormal-item.missing .abnormal-icon {
  background: oklch(0.92 0.10 25);
  color: var(--color-danger);
}

.abnormal-content {
  display: flex;
  flex-direction: column;
}

.abnormal-value {
  font-size: var(--text-xl);
  font-weight: 700;
}

.abnormal-label {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

/* 最近扫描 */
.recent-section {
  padding: 0 var(--space-4);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}

.section-title {
  font-size: var(--text-base);
  font-weight: 600;
  margin: 0;
}

.section-count {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.recent-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
}

.recent-item.matched {
  border-left: 4px solid var(--color-success);
}

.recent-item.surplus {
  border-left: 4px solid var(--color-warning);
}

.recent-item.missing {
  border-left: 4px solid var(--color-danger);
}

.recent-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: var(--text-lg);
  flex-shrink: 0;
}

.recent-content {
  flex: 1;
  min-width: 0;
}

.recent-code {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-primary-600);
}

.recent-name {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  margin: var(--space-1) 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recent-qty {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.qty-diff {
  margin-left: var(--space-2);
  font-weight: 500;
}

.qty-diff.surplus {
  color: var(--color-success);
}

.qty-diff.missing {
  color: var(--color-danger);
}

.recent-time {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* 底部操作栏 */
.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg-card);
  border-top: 1px solid var(--color-border);
  max-width: 480px;
  margin: 0 auto;
}

.bottom-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  height: 48px;
  border-radius: 12px;
  font-size: var(--text-base);
  font-weight: 500;
  border: none;
}

.bottom-btn svg {
  width: 20px;
  height: 20px;
}

.bottom-btn.secondary {
  background: var(--color-bg-elevated);
  color: var(--color-text-primary);
}

.bottom-btn.primary {
  background: var(--color-primary-500);
  color: white;
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  z-index: 100;
}

.modal-content {
  width: 100%;
  max-width: 360px;
  background: var(--color-bg-card);
  border-radius: 20px;
  overflow: hidden;
}

.modal-header {
  padding: var(--space-5);
  text-align: center;
  border-bottom: 1px solid var(--color-border-light);
}

.modal-title {
  font-size: var(--text-lg);
  font-weight: 600;
  margin: 0;
}

.modal-body {
  padding: var(--space-5);
}

.asset-info {
  text-align: center;
  margin-bottom: var(--space-5);
}

.asset-code {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-primary-600);
  background: var(--color-primary-50);
  padding: 4px 12px;
  border-radius: 6px;
  margin-bottom: var(--space-2);
}

.asset-name {
  display: block;
  font-size: var(--text-base);
  font-weight: 500;
}

.qty-section {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.qty-row {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.qty-label {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

.qty-value {
  font-size: var(--text-2xl);
  font-weight: 700;
}

.qty-value.expected {
  color: var(--color-text-tertiary);
}

.qty-divider {
  width: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
}

.qty-divider svg {
  width: 24px;
  height: 24px;
}

.qty-input-group {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.qty-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-elevated);
  border: none;
  border-radius: 10px;
  font-size: var(--text-xl);
  font-weight: 500;
  color: var(--color-text-primary);
}

.qty-btn:active {
  background: var(--color-primary-100);
  color: var(--color-primary-600);
}

.qty-input {
  width: 60px;
  height: 40px;
  text-align: center;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  font-size: var(--text-lg);
  font-weight: 600;
  background: var(--color-bg-page);
}

.qty-alert {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3);
  border-radius: 10px;
  font-size: var(--text-sm);
  font-weight: 500;
}

.qty-alert svg {
  width: 18px;
  height: 18px;
}

.qty-alert.surplus {
  background: oklch(0.92 0.08 145);
  color: var(--color-success);
}

.qty-alert.missing {
  background: oklch(0.92 0.10 25);
  color: var(--color-danger);
}

.modal-footer {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-5);
  border-top: 1px solid var(--color-border-light);
}

.modal-btn {
  flex: 1;
  height: 48px;
  border-radius: 12px;
  font-size: var(--text-base);
  font-weight: 500;
  border: none;
}

.modal-btn.cancel {
  background: var(--color-bg-elevated);
  color: var(--color-text-primary);
}

.modal-btn.confirm {
  background: var(--color-primary-500);
  color: white;
}
</style>
