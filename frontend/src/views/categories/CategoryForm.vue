<script setup lang="ts">
defineProps<{
  category: any
  saving: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save'): void
  (e: 'addAttribute'): void
  (e: 'removeAttribute', idx: number): void
}>()
</script>

<template>
  <div class="modal-overlay" role="dialog" aria-modal="true" @click.self="emit('close')" @keydown.esc="emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3 class="modal-title">{{ category?.id ? '编辑分类' : '新增分类' }}</h3>
        <button class="modal-close" aria-label="关闭" @click="emit('close')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="modal-body">
        <div class="form-grid">
          <div class="form-item">
            <label class="form-label">资产类目 <span class="required">*</span></label>
            <select v-model="category.资产类目" class="form-select">
              <option value="">请选择</option>
              <option value="固定资产类">固定资产类</option>
              <option value="低值易耗品">低值易耗品</option>
              <option value="无形资产类">无形资产类</option>
              <option value="文档资料类">文档资料类</option>
              <option value="特殊设备类">特殊设备类</option>
              <option value="其他资产">其他资产</option>
            </select>
          </div>
          <div class="form-item">
            <label class="form-label">物品分类 <span class="required">*</span></label>
            <input v-model="category.物品分类" type="text" class="form-input" placeholder="请输入物品分类" />
          </div>
          <div class="form-item">
            <label class="form-label">资产名称 <span class="required">*</span></label>
            <input v-model="category.资产名称" type="text" class="form-input" placeholder="请输入资产名称" />
          </div>
          <div class="form-item">
            <label class="form-label">资产编号 <span class="required">*</span></label>
            <input v-model="category.资产编号" type="text" class="form-input" placeholder="如：A-a00001" />
          </div>
          <div class="form-item">
            <label class="form-label">计量单位 <span class="required">*</span></label>
            <input v-model="category.计量单位" type="text" class="form-input" placeholder="如：台、个、张" />
          </div>
          <div class="form-item">
            <label class="form-label">警戒线</label>
            <input v-model="category.警戒线" type="number" class="form-input" placeholder="库存警戒数量" />
          </div>
          <div class="form-item full">
            <label class="form-label">备注</label>
            <textarea v-model="category.备注" class="form-textarea" placeholder="备注信息" rows="3" />
          </div>
          <!-- 属性模板 -->
          <div class="form-item full">
            <div class="attr-template-header">
              <label class="form-label">属性模板</label>
              <button type="button" class="attr-add-btn" @click="emit('addAttribute')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                  <line x1="12" y1="5" x2="12" y2="19"/>
                  <line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
                添加属性
              </button>
            </div>
            <div v-if="category.attributes && category.attributes.length > 0" class="attr-list">
              <div v-for="(attr, idx) in category.attributes" :key="idx" class="attr-item">
                <input v-model="attr.name" type="text" class="form-input attr-input" placeholder="属性名称" />
                <select v-model="attr.type" class="form-select attr-input">
                  <option value="text">文本</option>
                  <option value="number">数字</option>
                  <option value="select">下拉选择</option>
                </select>
                <label class="attr-required-label">
                  <input type="checkbox" v-model="attr.required" /> 必填
                </label>
                <input v-if="attr.type === 'select'" v-model="attr.options" type="text" class="form-input attr-input" placeholder="选项（逗号分隔）" />
                <button type="button" class="attr-del-btn" @click="emit('removeAttribute', idx)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>
            </div>
            <div v-else class="attr-empty">暂无自定义属性，点击"添加属性"配置</div>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-cancel" @click="emit('close')">取消</button>
        <button class="btn-confirm" @click="emit('save')" :disabled="saving">
          {{ saving ? '保存中...' : '确定保存' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal-content { background: var(--color-bg-elevated); border-radius: 16px; width: 90%; max-width: 600px; max-height: 90vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px; border-bottom: 1px solid var(--color-border); }
.modal-title { font-size: 18px; font-weight: 600; margin: 0; }
.modal-close { background: none; border: none; cursor: pointer; color: var(--color-text-secondary); padding: 4px; }
.modal-close svg { width: 20px; height: 20px; }
.modal-body { padding: 24px; }
.modal-footer { padding: 16px 24px; border-top: 1px solid var(--color-border); display: flex; justify-content: flex-end; gap: 12px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-item { display: flex; flex-direction: column; gap: 6px; }
.form-item.full { grid-column: 1 / -1; }
.form-label { font-size: 14px; font-weight: 500; }
.required { color: var(--color-danger); }
.form-input, .form-select { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: 8px; font-size: 14px; background: var(--color-bg); outline: none; }
.form-input:focus, .form-select:focus { border-color: var(--color-primary); }
.form-textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: 8px; font-size: 14px; background: var(--color-bg); outline: none; resize: vertical; }
.attr-template-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.attr-add-btn { display: flex; align-items: center; gap: 4px; padding: 4px 12px; border: 1px solid var(--color-primary); color: var(--color-primary); border-radius: 6px; background: none; cursor: pointer; font-size: 13px; }
.attr-list { display: flex; flex-direction: column; gap: 8px; }
.attr-item { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.attr-input { flex: 1; min-width: 100px; }
.attr-required-label { font-size: 13px; display: flex; align-items: center; gap: 4px; white-space: nowrap; }
.attr-del-btn { background: none; border: none; color: var(--color-danger); cursor: pointer; padding: 4px; }
.attr-empty { font-size: 13px; color: var(--color-text-secondary); padding: 12px 0; }
.btn-cancel { padding: 8px 20px; border-radius: 8px; border: 1px solid var(--color-border); background: var(--color-bg-elevated); cursor: pointer; font-size: 14px; }
.btn-confirm { padding: 8px 20px; border-radius: 8px; border: none; background: var(--color-primary); color: #fff; cursor: pointer; font-size: 14px; }
.btn-confirm:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
