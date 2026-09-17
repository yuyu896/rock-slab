<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAssetStocks, getFixedAssets } from '@/api/assets'
import { checkInventoryInstance, getInventoryReport, getInventoryTasks } from '@/api/inventories'
import { ElMessage } from 'element-plus'
import { useBarcodeScanner } from '@/composables/useBarcodeScanner'
import type { AssetStock, FixedAsset } from '@/types'

const route = useRoute()
const router = useRouter()

// ── 模式：查询（默认）/ 盘点（有进行中实例盘任务时可选，?task= 直达） ──
type ScanMode = 'query' | 'inventory'
const mode = ref<ScanMode>('query')

interface InvTaskLite { id: string; name: string; inventoryKind?: string }
const invTasks = ref<InvTaskLite[]>([])
const selectedTaskId = ref('')
const selectedTaskName = ref('')
const instanceItems = ref<any[]>([])
const invLoading = ref(false)

const invProgress = computed(() => {
  const matched = instanceItems.value.filter(x => x.result === 'matched').length
  return { matched, total: instanceItems.value.length }
})

async function loadInvTasks() {
  try {
    const { data } = await getInventoryTasks({ status: 'in_progress', pageSize: 50 } as any)
    invTasks.value = ((data as any).results || []).filter((t: any) => t.inventoryKind === 'instance')
  } catch {
    invTasks.value = []
  }
}

async function selectTask(id: string) {
  invLoading.value = true
  try {
    const { data } = await getInventoryReport(id)
    instanceItems.value = (data as any).items ?? []
    selectedTaskId.value = id
    selectedTaskName.value = invTasks.value.find(t => t.id === id)?.name || '盘点任务'
    mode.value = 'inventory'
  } catch {
    ElMessage.error('加载盘点清单失败')
  } finally {
    invLoading.value = false
  }
}

function switchMode(m: ScanMode) {
  mode.value = m
  if (m === 'inventory' && !selectedTaskId.value && invTasks.value.length === 1) {
    selectTask(invTasks.value[0].id)
  }
}

// ── 扫码会话：显式开始（权限弹窗不前置），会话内连扫不停机 ──
const videoRef = ref<HTMLVideoElement | null>(null)
const scanner = useBarcodeScanner(videoRef, { onDetect: handleCode })
const scanInput = ref('')
const busy = ref(false)

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && scanInput.value.trim()) {
    handleCode(scanInput.value.trim())
    scanInput.value = ''
  }
}

function handleCode(code: string) {
  if (busy.value) return
  if (mode.value === 'inventory') handleInventoryScan(code)
  else handleQueryScan(code)
}

// ── 反馈：哔声（iOS 亦有效）+ 震动（Android），失败低音调 ──
let audioCtx: AudioContext | null = null
/** 移动端自动播放策略：AudioContext 须在用户手势中创建/resume，否则 suspended 静音 */
function ensureAudio() {
  try {
    audioCtx = audioCtx ?? new (window.AudioContext || (window as any).webkitAudioContext)()
    if (audioCtx.state === 'suspended') void audioCtx.resume()
  } catch {
    // 音频不可用不影响扫码功能
  }
}
function feedback(ok: boolean) {
  ensureAudio()
  try {
    if (!audioCtx) return
    const osc = audioCtx.createOscillator()
    const gain = audioCtx.createGain()
    osc.connect(gain)
    gain.connect(audioCtx.destination)
    osc.type = 'square'
    osc.frequency.value = ok ? 1200 : 380
    gain.gain.setValueAtTime(0.3, audioCtx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.2)
    osc.start()
    osc.stop(audioCtx.currentTime + 0.2)
  } catch {
    // 音频失败不影响功能
  }
  navigator.vibrate?.(ok ? 80 : [60, 40, 60])
}

const audioState = ref('无音频')
function startScan() {
  ensureAudio()
  feedback(true) // 手势内立即发声：既是开始确认音，也是媒体音量的自检
  audioState.value = audioCtx?.state ?? '无音频'
  void scanner.start()
}

// ── 查询模式：扫码/输入 → 资产卡片 ──
const card = ref<{
  stockId: string
  code: string
  name: string
  status: string
  holder: string
  branch: string
} | null>(null)
const notFound = ref(false)
const queryLoading = ref(false)

async function handleQueryScan(code: string) {
  queryLoading.value = true
  notFound.value = false
  card.value = null
  busy.value = true
  try {
    const [stockRes, instRes] = await Promise.all([
      getAssetStocks({ keyword: code, pageSize: 5 }),
      getFixedAssets({ keyword: code, pageSize: 5 }),
    ])
    const rows: AssetStock[] = (stockRes.data as any).results || []
    const instances: FixedAsset[] = (instRes.data as any).results || []
    if (rows.length > 0) {
      const s = rows[0]
      card.value = {
        stockId: s.id,
        code: s.资产编号 || String(instances[0]?.内部编号 || code),
        name: s.资产名称 || instances[0]?.itemName || '',
        status: `${s.在库数量 ?? 0} 在库 / ${s.在用数量 ?? 0} 在用 / ${s.回收库数量 ?? 0} 回收库`,
        holder: instances[0]?.使用人 || '',
        branch: s.branchName || '',
      }
    } else if (instances.length > 0) {
      const inst = instances[0]
      card.value = {
        stockId: '',
        code: inst.内部编号,
        name: inst.itemName || '',
        status: inst.当前状态 || '',
        holder: inst.使用人 || '',
        branch: inst.branchName || '',
      }
    } else {
      notFound.value = true
      feedback(false)
    }
    if (card.value) feedback(true)
  } catch {
    ElMessage.error('查询失败')
    feedback(false)
  } finally {
    queryLoading.value = false
    busy.value = false
  }
}

function viewDetail() {
  if (card.value?.stockId) router.push(`/mobile/assets/${card.value.stockId}`)
}

// ── 盘点模式：清单精确匹配 → 自动打钩 → 流水 ──
interface FlowEntry { id: number; type: 'ok' | 'dup' | 'unknown'; text: string }
const flow = ref<FlowEntry[]>([])
let flowSeq = 0

async function handleInventoryScan(code: string) {
  if (!selectedTaskId.value) return
  busy.value = true
  try {
    const target = instanceItems.value.find(x =>
      x.instanceCode === code || (x.serialNumber && x.serialNumber === code))
    if (!target) {
      flow.value.unshift({ id: ++flowSeq, type: 'unknown', text: `清单外：${code}` })
      feedback(false)
      ElMessage.warning(`清单中未找到「${code}」`)
      return
    }
    if (target.result === 'matched') {
      flow.value.unshift({ id: ++flowSeq, type: 'dup', text: `已核对过：${target.instanceCode}` })
      feedback(false)
      return
    }
    await checkInventoryInstance(selectedTaskId.value, { instanceId: target.instance, found: true })
    target.result = 'matched'
    flow.value.unshift({
      id: ++flowSeq,
      type: 'ok',
      text: `已核对：${target.instanceCode}（${target.assetName || ''}${target.holder ? ' · ' + target.holder : ''}）`,
    })
    feedback(true)
  } catch {
    ElMessage.error('核对失败，请重试')
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  await loadInvTasks()
  const taskParam = String(route.query.task || '')
  if (taskParam && invTasks.value.some(t => t.id === taskParam)) {
    selectTask(taskParam)
  } else if (invTasks.value.length === 1) {
    // 唯一进行中任务时不自动切模式，仅露出入口（保持查询默认）
  }
})
</script>

<template>
  <div class="scan-terminal">
    <div class="page-header"><h1>扫码</h1></div>

    <!-- 模式开关：盘点项仅在有进行中实例盘任务时出现 -->
    <div class="mode-switch">
      <button class="mode-btn" :class="{ active: mode === 'query' }" @click="switchMode('query')">查询</button>
      <button
        v-if="invTasks.length"
        class="mode-btn"
        :class="{ active: mode === 'inventory' }"
        @click="switchMode('inventory')"
      >盘点</button>
    </div>

    <!-- 扫码会话区 -->
    <div class="camera-zone">
      <video v-show="scanner.active.value" ref="videoRef" class="camera-video" playsinline muted></video>
      <button v-if="!scanner.active.value" class="start-btn" @click="startScan()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/>
          <line x1="7" y1="12" x2="17" y2="12"/>
        </svg>
        <span>开始扫码</span>
      </button>
      <button v-else class="stop-btn" @click="scanner.stop()">停止扫码</button>
      <p v-if="scanner.error.value" class="camera-error">{{ scanner.error.value }}</p>
      <p v-if="scanner.active.value" class="scan-debug">引擎 {{ scanner.engine }} · {{ scanner.resolution.value }} · 已分析 {{ scanner.frames.value }} 帧 · 音频 {{ audioState }}{{ scanner.lastError.value ? ' · ' + scanner.lastError.value : '' }}</p>
    </div>

    <!-- 手动输入兜底（扫码枪/手输与摄像头同链） -->
    <div class="manual-row">
      <input
        v-model="scanInput"
        type="text"
        class="manual-input"
        placeholder="扫码枪或手动输入编号，回车确认"
        @keydown="handleKeydown"
      />
    </div>

    <!-- 查询模式：资产卡片 -->
    <template v-if="mode === 'query'">
      <p v-if="queryLoading" class="hint-text">查询中…</p>
      <div v-if="card" class="asset-card" @click="viewDetail">
        <div class="card-row card-code">{{ card.code }}</div>
        <div class="card-row card-name">{{ card.name }}</div>
        <div class="card-meta">
          <span>状态：{{ card.status }}</span>
          <span v-if="card.holder">使用人：{{ card.holder }}</span>
          <span v-if="card.branch">分公司：{{ card.branch }}</span>
        </div>
        <div v-if="card.stockId" class="card-link">查看详情 ›</div>
      </div>
      <p v-else-if="notFound" class="hint-text warn">未找到对应资产，可继续扫下一个</p>
    </template>

    <!-- 盘点模式：任务选择 / 进度与流水 -->
    <template v-else>
      <div v-if="!selectedTaskId" class="task-picker">
        <p class="hint-text">选择进行中的盘点任务</p>
        <button
          v-for="t in invTasks"
          :key="t.id"
          class="task-option"
          :disabled="invLoading"
          @click="selectTask(t.id)"
        >{{ t.name }}</button>
      </div>
      <template v-else>
        <div class="inv-progress">
          <span class="inv-name">{{ selectedTaskName }}</span>
          <span class="inv-count">{{ invProgress.matched }} / {{ invProgress.total }}</span>
        </div>
        <div class="flow-list">
          <div v-for="entry in flow" :key="entry.id" class="flow-item" :class="entry.type">
            <span class="flow-mark">{{ entry.type === 'ok' ? '✓' : entry.type === 'dup' ? '↻' : '⚠' }}</span>
            <span>{{ entry.text }}</span>
          </div>
          <p v-if="!flow.length" class="hint-text">对准标签开始扫码，识别后自动打钩</p>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.scan-terminal { padding: var(--space-4); min-height: 100vh; }
.page-header { margin-bottom: var(--space-3); }
.page-header h1 { font-size: 20px; font-weight: 600; color: var(--color-text-primary); }

.mode-switch { display: flex; gap: var(--space-2); margin-bottom: var(--space-3); }
.mode-btn { flex: 1; height: 40px; border: 1px solid var(--color-border); border-radius: 10px; background: var(--color-bg-card); color: var(--color-text-secondary); font-size: 14px; cursor: pointer; }
.mode-btn.active { border-color: var(--color-primary-500); color: var(--color-primary-500); background: var(--color-primary-50); }

.camera-zone { position: relative; height: 260px; border-radius: 14px; overflow: hidden; background: var(--color-bg-card); border: 1px solid var(--color-border); margin-bottom: var(--space-3); }
.camera-video { width: 100%; height: 100%; object-fit: cover; }
.start-btn { position: absolute; inset: 0; margin: auto; width: 150px; height: 96px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; border: 2px dashed var(--color-primary-500); border-radius: 16px; background: var(--color-bg-card); color: var(--color-primary-500); font-size: 15px; cursor: pointer; }
.start-btn svg { width: 30px; height: 30px; }
.stop-btn { position: absolute; right: 10px; bottom: 10px; padding: 6px 14px; border: none; border-radius: 8px; background: rgba(0,0,0,0.55); color: #fff; font-size: 12px; cursor: pointer; }
.camera-error { position: absolute; left: 0; right: 0; bottom: 10px; margin: 0; text-align: center; font-size: 12px; color: var(--color-warning); padding: 0 12px; }
.scan-debug { position: absolute; left: 10px; top: 8px; margin: 0; font-size: 10px; color: rgba(255,255,255,0.75); font-family: var(--font-mono); text-shadow: 0 0 2px rgba(0,0,0,0.6); }

.manual-row { margin-bottom: var(--space-3); }
.manual-input { width: 100%; height: 44px; padding: 0 var(--space-3); border: 1px solid var(--color-border); border-radius: 10px; background: var(--color-bg-card); font-size: 15px; text-align: center; }
.manual-input:focus { outline: none; border-color: var(--color-primary-500); }

.hint-text { font-size: 13px; color: var(--color-text-tertiary); text-align: center; }
.hint-text.warn { color: var(--color-warning); }

.asset-card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 14px; padding: var(--space-4); }
.card-code { font-family: var(--font-mono); font-size: 13px; color: var(--color-text-tertiary); }
.card-name { font-size: 18px; font-weight: 600; color: var(--color-text-primary); margin: 4px 0 8px; }
.card-meta { display: flex; flex-direction: column; gap: 4px; font-size: 13px; color: var(--color-text-secondary); }
.card-link { margin-top: 10px; font-size: 13px; color: var(--color-primary-500); }

.task-picker { display: flex; flex-direction: column; gap: var(--space-2); }
.task-option { height: 48px; border: 1px solid var(--color-border); border-radius: 10px; background: var(--color-bg-card); font-size: 14px; color: var(--color-text-primary); cursor: pointer; text-align: left; padding: 0 var(--space-3); }

.inv-progress { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); }
.inv-name { font-size: 14px; font-weight: 600; color: var(--color-text-primary); }
.inv-count { font-size: 14px; color: var(--color-primary-500); font-weight: 600; }

.flow-list { display: flex; flex-direction: column; gap: 6px; }
.flow-item { display: flex; gap: 8px; align-items: baseline; font-size: 13px; padding: 8px 10px; border-radius: 8px; background: var(--color-bg-card); border: 1px solid var(--color-border); color: var(--color-text-primary); }
.flow-item .flow-mark { font-weight: 700; }
.flow-item.ok .flow-mark { color: var(--color-success); }
.flow-item.dup { color: var(--color-text-tertiary); }
.flow-item.unknown .flow-mark { color: var(--color-warning); }
</style>
