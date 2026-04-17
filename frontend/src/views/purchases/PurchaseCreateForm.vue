<script setup lang="ts">
import { ref, computed } from 'vue'
import { formatMoney } from '@/utils/format'

defineProps<{
  branchOptions: { value: string; label: string }[]
}>()

const emit = defineEmits<{
  (e: 'back'): void
  (e: 'submit', order: any): void
  (e: 'saveDraft', order: any): void
}>()

const newOrder = ref({
  branch: '',
  supplier: '',
  items: [
    { code: '', name: '', spec: '', qty: 1, price: 0 }
  ],
  purchaseDate: '',
  isRent: false,
  remark: ''
})

const totalAmount = computed(() => {
  return newOrder.value.items.reduce((sum, item) => sum + item.qty * item.price, 0)
})

function addItem() {
  newOrder.value.items.push({ code: '', name: '', spec: '', qty: 1, price: 0 })
}

function removeItem(index: number) {
  if (newOrder.value.items.length > 1) {
    newOrder.value.items.splice(index, 1)
  }
}

function handleSubmit() {
  emit('submit', newOrder.value)
}

function handleSaveDraft() {
  emit('saveDraft', newOrder.value)
}
</script>

<template>
  <div class="create-view">
    <div class="create-header">
      <button class="back-btn" @click="emit('back')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
        返回列表
      </button>
      <h2 class="create-title">新建采购入库单</h2>
    </div>

    <div class="create-content">
      <!-- 基本信息 -->
      <div class="form-section">
        <h3 class="section-title">基本信息</h3>
        <div class="form-grid">
          <div class="form-item">
            <label class="form-label">入库分公司 <span class="required">*</span></label>
            <select v-model="newOrder.branch" class="form-select">
              <option value="">请选择分公司</option>
              <option v-for="opt in branchOptions.slice(1)" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
          <div class="form-item">
            <label class="form-label">供应商 <span class="required">*</span></label>
            <input v-model="newOrder.supplier" type="text" class="form-input" placeholder="请输入供应商名称" />
          </div>
          <div class="form-item">
            <label class="form-label">采购日期 <span class="required">*</span></label>
            <input v-model="newOrder.purchaseDate" type="date" class="form-input" />
          </div>
          <div class="form-item checkbox-item">
            <label class="checkbox-label">
              <input v-model="newOrder.isRent" type="checkbox" />
              <span>是否租用资产</span>
            </label>
          </div>
        </div>
      </div>

      <!-- 物品明细 -->
      <div class="form-section">
        <div class="section-header">
          <h3 class="section-title">物品明细</h3>
          <button class="add-row-btn" @click="addItem">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            添加物品
          </button>
        </div>

        <div class="items-table">
          <div class="items-header">
            <span class="col-code">资产编号</span>
            <span class="col-name">资产名称</span>
            <span class="col-spec">规格型号</span>
            <span class="col-qty">数量</span>
            <span class="col-price">单价</span>
            <span class="col-amount">金额</span>
            <span class="col-action"></span>
          </div>
          <div
            v-for="(item, index) in newOrder.items"
            :key="index"
            class="items-row"
          >
            <input v-model="item.code" type="text" class="item-input code" placeholder="资产编号" />
            <input v-model="item.name" type="text" class="item-input name" placeholder="资产名称" />
            <input v-model="item.spec" type="text" class="item-input spec" placeholder="规格型号" />
            <input v-model="item.qty" type="number" class="item-input qty" min="1" />
            <input v-model="item.price" type="number" class="item-input price" min="0" placeholder="0.00" />
            <span class="item-amount">{{ formatMoney(item.qty * item.price) }}</span>
            <button
              class="remove-btn"
              :disabled="newOrder.items.length === 1"
              @click="removeItem(index)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        </div>

        <div class="items-summary">
          <div class="summary-row">
            <span class="summary-label">合计数量：</span>
            <span class="summary-value">{{ newOrder.items.reduce((sum, item) => sum + item.qty, 0) }} 件</span>
          </div>
          <div class="summary-row highlight">
            <span class="summary-label">合计金额：</span>
            <span class="summary-value">{{ formatMoney(totalAmount) }}</span>
          </div>
        </div>
      </div>

      <!-- 备注 -->
      <div class="form-section">
        <h3 class="section-title">备注信息</h3>
        <textarea
          v-model="newOrder.remark"
          class="form-textarea"
          placeholder="请输入备注信息..."
          rows="3"
        />
      </div>

      <!-- 操作按钮 -->
      <div class="form-actions">
        <button class="btn-cancel" @click="emit('back')">取消</button>
        <button class="btn-draft" @click="handleSaveDraft">保存草稿</button>
        <button class="btn-submit" @click="handleSubmit">提交审批</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.create-view { max-width: 1000px; }
.create-header { display: flex; align-items: center; gap: var(--space-4); margin-bottom: var(--space-6); }
.back-btn { display: flex; align-items: center; gap: var(--space-2); background: transparent; border: none; color: var(--color-text-secondary); font-size: var(--text-sm); cursor: pointer; }
.back-btn svg { width: 18px; height: 18px; }
.create-title { font-size: var(--text-xl); font-weight: 600; margin: 0; }
.create-content { background: var(--color-bg-card); border-radius: 12px; border: 1px solid var(--color-border); padding: var(--space-6); }
.form-section { margin-bottom: var(--space-6); }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-4); }
.section-title { font-size: var(--text-base); font-weight: 600; margin: 0 0 var(--space-4) 0; padding-bottom: var(--space-3); border-bottom: 1px solid var(--color-border-light); }
.section-header .section-title { margin: 0; border: none; padding: 0; }
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-4); }
.form-item { display: flex; flex-direction: column; gap: var(--space-2); }
.form-label { font-size: var(--text-sm); font-weight: 500; color: var(--color-text-primary); }
.required { color: var(--color-danger); }
.form-input, .form-select { height: 40px; padding: 0 var(--space-3); border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-page); font-size: var(--text-sm); }
.checkbox-item { flex-direction: row; align-items: center; padding-top: var(--space-6); }
.checkbox-label { display: flex; align-items: center; gap: var(--space-2); cursor: pointer; }
.add-row-btn { display: flex; align-items: center; gap: var(--space-2); background: var(--color-primary-50); border: 1px solid var(--color-primary-200); border-radius: 8px; padding: var(--space-2) var(--space-4); color: var(--color-primary-600); font-size: var(--text-sm); cursor: pointer; }
.add-row-btn svg { width: 16px; height: 16px; }
.items-table { border: 1px solid var(--color-border); border-radius: 8px; overflow: hidden; }
.items-header { display: grid; grid-template-columns: 120px 1fr 120px 80px 100px 100px 40px; gap: var(--space-2); padding: var(--space-3) var(--space-4); background: var(--color-bg-elevated); font-size: var(--text-sm); font-weight: 500; color: var(--color-text-secondary); }
.items-row { display: grid; grid-template-columns: 120px 1fr 120px 80px 100px 100px 40px; gap: var(--space-2); padding: var(--space-2) var(--space-4); border-top: 1px solid var(--color-border-light); align-items: center; }
.item-input { height: 36px; padding: 0 var(--space-2); border: 1px solid var(--color-border); border-radius: 6px; background: var(--color-bg-page); font-size: var(--text-sm); }
.item-input:focus { outline: none; border-color: var(--color-primary-400); }
.item-amount { font-weight: 500; color: var(--color-text-primary); }
.remove-btn { width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; background: transparent; border: none; border-radius: 6px; color: var(--color-text-tertiary); cursor: pointer; }
.remove-btn:hover:not(:disabled) { background: oklch(0.92 0.10 25); color: var(--color-danger); }
.remove-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.remove-btn svg { width: 16px; height: 16px; }
.items-summary { display: flex; justify-content: flex-end; gap: var(--space-8); padding: var(--space-4); background: var(--color-bg-elevated); border-top: 1px solid var(--color-border); margin-top: var(--space-3); border-radius: 8px; }
.summary-row { display: flex; align-items: center; gap: var(--space-2); }
.summary-label { font-size: var(--text-sm); color: var(--color-text-secondary); }
.summary-value { font-size: var(--text-lg); font-weight: 600; color: var(--color-text-primary); }
.summary-row.highlight .summary-value { color: var(--color-primary-600); }
.form-textarea { width: 100%; padding: var(--space-3); border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-page); font-size: var(--text-sm); resize: vertical; }
.form-actions { display: flex; justify-content: flex-end; gap: var(--space-3); padding-top: var(--space-4); border-top: 1px solid var(--color-border); margin-top: var(--space-6); }
.btn-cancel, .btn-draft, .btn-submit { height: 40px; padding: 0 var(--space-6); border-radius: 8px; font-size: var(--text-sm); font-weight: 500; cursor: pointer; }
.btn-cancel { background: var(--color-bg-card); border: 1px solid var(--color-border); color: var(--color-text-primary); }
.btn-draft { background: var(--color-bg-elevated); border: 1px solid var(--color-border); color: var(--color-text-primary); }
.btn-submit { background: var(--color-primary-500); border: none; color: white; }
@media (max-width: 768px) { .form-grid { grid-template-columns: 1fr; } .items-header, .items-row { grid-template-columns: 1fr; } }
</style>
