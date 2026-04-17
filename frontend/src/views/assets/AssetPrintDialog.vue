<script setup lang="ts">
import { nextTick, watch } from 'vue'
import JsBarcode from 'jsbarcode'
import type { Asset } from '@/types'

const props = defineProps<{
  visible: boolean
  assets: Asset[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

function renderBarcodes() {
  nextTick(() => {
    props.assets.forEach(asset => {
      const el = document.getElementById(`barcode-${asset.id}`)
      if (el) {
        try {
          JsBarcode(el, asset.资产编号 || '', {
            format: 'CODE128',
            width: 2,
            height: 60,
            displayValue: true,
            fontSize: 14,
            margin: 5,
          })
        } catch {
          // barcode generation failed silently
        }
      }
    })
  })
}

function executePrint() {
  window.print()
}

watch(() => props.visible, (val) => {
  if (val) renderBarcodes()
})
</script>

<template>
  <div v-if="visible" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-content print-modal">
      <div class="modal-header">
        <h3>打印标签 ({{ assets.length }} 项)</h3>
        <button class="modal-close" @click="emit('close')">&times;</button>
      </div>
      <div class="modal-body print-body">
        <div id="print-area" class="print-labels">
          <div v-for="asset in assets" :key="asset.id" class="print-label">
            <div class="label-barcode">
              <svg :id="'barcode-' + asset.id"></svg>
            </div>
            <div class="label-info">
              <div class="label-name">{{ asset.资产名称 }}</div>
              <div class="label-code">{{ asset.资产编号 }}</div>
              <div class="label-branch">{{ asset.分公司 }}</div>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-cancel" @click="emit('close')">关闭</button>
        <button class="btn-confirm" @click="executePrint">打印</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal-content { background: var(--color-bg-elevated); border-radius: 16px; width: 90%; max-width: 640px; max-height: 90vh; overflow-y: auto; }
.print-modal { max-width: 800px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px; border-bottom: 1px solid var(--color-border); }
.modal-header h3 { margin: 0; font-size: 18px; }
.modal-close { background: none; border: none; font-size: 24px; cursor: pointer; color: var(--color-text-secondary); }
.modal-body { padding: 24px; }
.modal-footer { padding: 16px 24px; border-top: 1px solid var(--color-border); display: flex; justify-content: flex-end; gap: 12px; }
.print-labels { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.print-label { border: 1px solid var(--color-border); border-radius: 8px; padding: 12px; display: flex; gap: 12px; align-items: center; }
.label-barcode svg { max-width: 120px; }
.label-info { display: flex; flex-direction: column; gap: 2px; }
.label-name { font-weight: 600; font-size: 14px; }
.label-code { font-family: monospace; font-size: 13px; color: var(--color-primary); }
.label-branch { font-size: 12px; color: var(--color-text-secondary); }
.btn-cancel { padding: 8px 20px; border-radius: 8px; border: 1px solid var(--color-border); background: var(--color-bg-elevated); cursor: pointer; font-size: 14px; }
.btn-confirm { padding: 8px 20px; border-radius: 8px; border: none; background: var(--color-primary); color: #fff; cursor: pointer; font-size: 14px; }
</style>
