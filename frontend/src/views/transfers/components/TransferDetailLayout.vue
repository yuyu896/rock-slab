<script setup lang="ts">
import { useRouter } from 'vue-router'
import TransferLinesTable from './TransferLinesTable.vue'
import type { TransferDocument } from '@/types'
import type { TransferType } from '@/constants'

/** 单据详情统一布局：一行元信息 + 类型专属字段（slot）+ 明细表 + 审批/编辑按钮（slot） */
const props = defineProps<{
  title: string
  backPath: string
  doc: TransferDocument | null
  type: TransferType
  loading?: boolean
}>()

const router = useRouter()

const emit = defineEmits<{
  (e: 'approve'): void
  (e: 'reject'): void
}>()

function branchText(doc: TransferDocument) {
  if (doc.调出分公司 && doc.调入分公司) return `${doc.调出分公司} → ${doc.调入分公司}`
  return doc.调出分公司 || doc.调入分公司 || '-'
}
</script>

<template>
  <div class="detail-page">
    <div class="page-header">
      <button class="back-btn" @click="router.push(props.backPath)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        返回
      </button>
      <h1 class="page-title">{{ title }}</h1>
    </div>

    <div v-if="loading" class="state-text">加载中...</div>
    <div v-else-if="!doc" class="state-text">未找到记录</div>

    <div v-else class="detail-body">
      <!-- 一行元信息 -->
      <div class="meta-row">
        <span class="meta-item"><label>单号</label><span class="mono">{{ doc.单据编号 || '-' }}</span></span>
        <span class="meta-item"><label>日期</label><span class="mono">{{ doc.调拨日期 || '-' }}</span></span>
        <span class="meta-item"><label>分公司</label><span>{{ branchText(doc) }}</span></span>
        <span class="meta-item"><label>创建人</label><span>{{ doc.创建人 || '-' }}</span></span>
        <span class="meta-item"><label>审批</label><span>{{ doc.审批人 || '-' }}{{ doc.审批时间 ? ` · ${String(doc.审批时间).slice(0, 16).replace('T', ' ')}` : '' }}</span></span>
        <span class="meta-item"><label>状态</label><span class="status-text">{{ doc.审批状态 }}</span></span>
      </div>

      <slot name="extra-view" :doc="doc" />

      <h3 class="lines-title">明细（{{ doc.lines?.length ?? 0 }} 项）</h3>
      <TransferLinesTable :lines="doc.lines ?? []" :type="props.type" />

      <slot name="extra-edit" :doc="doc" />

      <div class="detail-footer">
        <slot name="footer" :doc="doc">
          <template v-if="doc.审批状态 === '待审批'">
            <button class="btn-approve" @click="emit('approve')">通过</button>
            <button class="btn-reject" @click="emit('reject')">驳回</button>
          </template>
        </slot>
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail-page { max-width: 1080px; margin: 0 auto; }
.page-header { display: flex; align-items: center; gap: var(--space-4); margin-bottom: var(--space-6); }
.back-btn { display: inline-flex; align-items: center; gap: var(--space-1); height: 36px; padding: 0 var(--space-3); background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; font-size: var(--text-sm); color: var(--color-text-secondary); cursor: pointer; }
.back-btn:hover { color: var(--color-primary-500); border-color: var(--color-primary-300); }
.back-btn svg { width: 16px; height: 16px; }
.page-title { font-size: var(--text-xl); font-weight: 600; color: var(--color-text-primary); margin: 0; }
.state-text { text-align: center; color: var(--color-text-secondary); padding: var(--space-8); }
.detail-body { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 16px; padding: var(--space-6); display: flex; flex-direction: column; gap: var(--space-5); }
.meta-row { display: flex; flex-wrap: wrap; gap: var(--space-2) var(--space-6); padding-bottom: var(--space-4); border-bottom: 1px solid var(--color-border); }
.meta-item { display: inline-flex; align-items: baseline; gap: 6px; font-size: var(--text-sm); }
.meta-item label { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.meta-item span { color: var(--color-text-primary); }
.mono { font-family: var(--font-mono); }
.status-text { font-weight: 600; }
.lines-title { font-size: 15px; font-weight: 600; margin: 0; }
.detail-footer { display: flex; justify-content: flex-end; gap: var(--space-3); }
.btn-approve { height: 40px; padding: 0 20px; border-radius: 8px; border: none; background: var(--color-primary-500); color: #fff; cursor: pointer; font-size: var(--text-sm); }
.btn-reject { height: 40px; padding: 0 20px; border-radius: 8px; border: none; background: oklch(0.92 0.10 25); color: var(--color-danger); cursor: pointer; font-size: var(--text-sm); }
</style>
