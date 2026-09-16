<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import QRCode from 'qrcode'
import { labelFileName, renderLabelDataUrl } from '@/utils/labelImage'
import type { LabelAssetShape } from '@/utils/labelImage'
/* 打印对象为字段映射后的宽松形状（内部编号/序列号/品目信息） */
type Asset = Record<string, any>

const props = defineProps<{
  visible: boolean
  assets: Array<Asset | Record<string, any>>
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

type PaperSize = '60x40' | 'a4'
const PAPER_KEY = 'rock_slab_label_paper'

const paper = ref<PaperSize>(localStorage.getItem(PAPER_KEY) === 'a4' ? 'a4' : '60x40')

/* @page 无法按 class 作用域，用专属 style 元素随纸型改写 */
let pageStyle: HTMLStyleElement | null = null

function applyPageSize(size: PaperSize) {
  if (!pageStyle) {
    pageStyle = document.createElement('style')
    pageStyle.id = 'label-page-size'
    document.head.appendChild(pageStyle)
  }
  pageStyle.textContent = size === '60x40'
    ? '@page { size: 60mm 40mm; margin: 0; }'
    : '@page { size: A4; margin: 8mm; }'
}

function switchPaper(size: PaperSize) {
  paper.value = size
  localStorage.setItem(PAPER_KEY, size)
  applyPageSize(size)
  fitLabelLines()
}

async function renderQrCodes() {
  await nextTick()
  await Promise.all(props.assets.map(async asset => {
    const el = document.getElementById(`qr-${asset.id}`)
    if (!el || !asset.内部编号) return
    try {
      const svg = await QRCode.toString(String(asset.内部编号), {
        type: 'svg',
        errorCorrectionLevel: 'M',
        margin: 0,
      })
      el.innerHTML = svg
    } catch {
      // QR 生成失败静默（内部编号为必填字段）
    }
  }))
  fitLabelLines()
}

/** 单签内容不越界：超宽行逐步缩号（下限 2.2mm），保持单行不换行 */
function fitLabelLines() {
  const minPx = 2.2 * (96 / 25.4)
  document.querySelectorAll<HTMLElement>('.print-label .fit').forEach(line => {
    line.style.fontSize = ''
    let size = parseFloat(getComputedStyle(line).fontSize)
    while (line.scrollWidth > line.clientWidth && size > minPx) {
      size -= 0.4
      line.style.fontSize = `${size}px`
    }
  })
}

function executePrint() {
  window.print()
}

// ── 导出图片（第二输出通道：App 生态蓝牙标签机经相册图片打印） ──
const exportMode = ref(false)
const exportItems = ref<Array<{ url: string; name: string }>>([])
const exporting = ref(false)

async function openExport() {
  exporting.value = true
  exportMode.value = true
  try {
    exportItems.value = await Promise.all(props.assets.map(async asset => {
      const shape = asset as unknown as LabelAssetShape
      return { url: await renderLabelDataUrl(shape), name: labelFileName(shape) }
    }))
  } catch {
    exportMode.value = false
  } finally {
    exporting.value = false
  }
}

function backToPreview() {
  exportMode.value = false
}

function triggerDownload(item: { url: string; name: string }) {
  const a = document.createElement('a')
  a.href = item.url
  a.download = item.name
  document.body.appendChild(a)
  a.click()
  a.remove()
}

function downloadAll() {
  exportItems.value.forEach((item, i) => setTimeout(() => triggerDownload(item), i * 200))
}

watch(() => props.visible, (val) => {
  if (val) renderQrCodes()
})

onMounted(() => applyPageSize(paper.value))
onBeforeUnmount(() => {
  pageStyle?.remove()
  pageStyle = null
})
</script>

<template>
  <!-- Teleport 到 body：与 #app 平级，打印媒体查询隐藏 #app 后仅输出本弹窗的标签区 -->
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click.self="emit('close')">
      <div class="modal-content print-modal" :class="paper === '60x40' ? 'paper-60x40' : 'paper-a4'">
        <div class="modal-header">
          <h3>{{ exportMode ? '导出标签图片' : `打印标签（${assets.length} 项）` }}</h3>
          <div v-if="!exportMode" class="paper-switch">
            <button :class="{ active: paper === '60x40' }" @click="switchPaper('60x40')">60×40 标签纸</button>
            <button :class="{ active: paper === 'a4' }" @click="switchPaper('a4')">A4 双列</button>
          </div>
          <button class="modal-close" @click="emit('close')">&times;</button>
        </div>
        <div v-if="!exportMode" class="modal-body print-body">
          <p class="print-hint">打印时请选择：实际大小 / 100%（勿用「适应页面」）</p>
          <div id="print-area" class="print-labels">
            <div v-for="asset in assets" :key="asset.id" class="print-label">
              <div class="label-qr">
                <div :id="'qr-' + asset.id" class="qr-box"></div>
              </div>
              <div class="label-info">
                <div class="label-code fit">{{ asset.内部编号 }}</div>
                <div v-if="asset.序列号" class="label-sn fit">SN: {{ asset.序列号 }}</div>
                <div class="label-name fit">{{ asset.资产名称 }}</div>
                <div class="label-aux fit">品目 {{ asset.品目编号 }} · {{ asset.分公司 }}</div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="modal-body export-view">
          <p class="print-hint">标签机 App 打印时请选「原尺寸 / 60×40」；手机浏览器可长按图片保存到相册</p>
          <p v-if="exporting" class="export-loading">渲染中…</p>
          <div class="export-list">
            <div v-for="item in exportItems" :key="item.name" class="export-item">
              <img :src="item.url" :alt="item.name" />
              <button class="btn-cancel" @click="triggerDownload(item)">下载</button>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="emit('close')">关闭</button>
          <button v-if="!exportMode" class="btn-export" :disabled="exporting" @click="openExport">导出图片</button>
          <template v-else>
            <button class="btn-export" @click="downloadAll" :disabled="!exportItems.length">全部下载</button>
            <button class="btn-confirm" @click="backToPreview">返回打印</button>
          </template>
          <button v-if="!exportMode" class="btn-confirm" @click="executePrint">打印</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal-content { background: var(--color-bg-elevated); border-radius: 16px; width: 90%; max-width: 640px; max-height: 90vh; overflow-y: auto; }
.print-modal { max-width: 800px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px; border-bottom: 1px solid var(--color-border); gap: 12px; }
.modal-header h3 { margin: 0; font-size: 18px; white-space: nowrap; }
.modal-close { background: none; border: none; font-size: 24px; cursor: pointer; color: var(--color-text-secondary); }
.paper-switch { display: flex; gap: 8px; margin-left: auto; }
.paper-switch button { padding: 6px 14px; border-radius: 8px; border: 1px solid var(--color-border); background: var(--color-bg-elevated); cursor: pointer; font-size: 13px; }
.paper-switch button.active { border-color: var(--color-primary); color: var(--color-primary); background: var(--color-primary-50, transparent); }
.modal-body { padding: 24px; }
.print-hint { margin: 0 0 16px; font-size: 13px; color: var(--color-warning, #b8860b); }
.modal-footer { padding: 16px 24px; border-top: 1px solid var(--color-border); display: flex; justify-content: flex-end; gap: 12px; }
.btn-cancel { padding: 8px 20px; border-radius: 8px; border: 1px solid var(--color-border); background: var(--color-bg-elevated); cursor: pointer; font-size: 14px; }
.btn-confirm { padding: 8px 20px; border-radius: 8px; border: none; background: var(--color-primary); color: #fff; cursor: pointer; font-size: 14px; }
.btn-export { padding: 8px 20px; border-radius: 8px; border: 1px solid var(--color-primary); background: var(--color-bg-elevated); color: var(--color-primary); cursor: pointer; font-size: 14px; }
.btn-export:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── 导出图片视图：标签 PNG 预览 + 逐张/全部下载 ── */
.export-view .export-loading { color: var(--color-text-secondary); font-size: 14px; }
.export-list { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.export-item { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; }
.export-item img { width: 240px; border: 1px solid var(--color-border); background: #fff; user-select: element; -webkit-user-select: element; -webkit-touch-callout: default; }

/* QR 码：13×13mm 定死 + 2mm 静区，黑码白底 */
.label-qr { flex: 0 0 auto; }
.qr-box { width: 13mm; height: 13mm; padding: 2mm; box-sizing: content-box; background: #fff; }
.qr-box :deep(svg) { width: 13mm; height: 13mm; display: block; }

/* ── 60×40 单签（标签打印机，默认）：一页一签，固定高度盒防越界 ── */
.paper-60x40 .print-labels { display: flex; flex-direction: column; gap: 4mm; align-items: flex-start; }
.paper-60x40 .print-label {
  width: 60mm; height: 40mm; box-sizing: border-box; padding: 1.5mm;
  display: flex; gap: 1.5mm; align-items: center;
  border: 0.3mm solid #999; background: #fff; color: #000; overflow: hidden;
}
.paper-60x40 .print-label:not(:last-child) { break-after: page; page-break-after: always; }
.paper-60x40 .label-info { display: flex; flex-direction: column; gap: 0.6mm; min-width: 0; flex: 1; }
.paper-60x40 .label-code { font-family: var(--font-mono, monospace); font-size: 3.2mm; font-weight: 700; color: #000; }
.paper-60x40 .label-sn { font-family: var(--font-mono, monospace); font-size: 2.8mm; color: #000; }
.paper-60x40 .label-name { font-size: 3mm; font-weight: 600; color: #000; }
.paper-60x40 .label-aux { font-size: 2.4mm; color: #444; }
.paper-60x40 .fit { white-space: nowrap; overflow: hidden; }

/* ── A4 双列（普通打印机）：卡片流式分页 ── */
.paper-a4 .print-labels { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.paper-a4 .print-label { border: 1px solid var(--color-border); border-radius: 8px; padding: 12px; display: flex; gap: 12px; align-items: center; }
.paper-a4 .qr-box { width: 18mm; height: 18mm; }
.paper-a4 .qr-box :deep(svg) { width: 18mm; height: 18mm; }
.paper-a4 .label-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.paper-a4 .label-code { font-family: var(--font-mono, monospace); font-size: 14px; font-weight: 700; color: var(--color-primary); }
.paper-a4 .label-sn { font-family: var(--font-mono, monospace); font-size: 12px; color: var(--color-text-secondary); }
.paper-a4 .label-name { font-size: 14px; font-weight: 600; }
.paper-a4 .label-aux { font-size: 12px; color: var(--color-text-secondary); }

/* 打印态：只输出标签（配合下方非 scoped 块隐藏 #app），配色固定值绕开深色模式 */
@media print {
  .modal-overlay { position: static; background: none; display: block; }
  .modal-content { max-height: none; overflow: visible; width: 100%; max-width: none; border: none; border-radius: 0; background: #fff; }
  .modal-header, .modal-footer, .print-hint { display: none; }
  .modal-body { padding: 0; }
  .export-view { display: none !important; }
  .paper-60x40 .print-labels { gap: 0; }
  .paper-a4 .print-label { break-inside: avoid; page-break-inside: avoid; border-color: #999; background: #fff; }
  .paper-a4 .label-code { color: #000; }
  .paper-a4 .label-sn, .paper-a4 .label-aux { color: #444; }
}
</style>

<!-- 非 scoped：打印输出隔离。本组件是唯一打印源，规则随组件走：
     打印时隐藏应用壳（#app），仅输出 Teleport 到 body 的标签区；白底固定不受深色模式影响 -->
<style>
@media print {
  #app { display: none !important; }
  body { background: #fff !important; }
}
</style>
