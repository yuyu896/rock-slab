<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { transferAsset } from '@/api/transfers'
import { getCategories } from '@/api/categories'
import { getBranches } from '@/api/branches'
import { useUserStore } from '@/store/user'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import type { Category, Branch } from '@/types'

const router = useRouter()
const userStore = useUserStore()

const form = ref({
  调拨日期: '',
  资产编号: '',
  资产名称: '',
  fromBranch: '',
  toBranch: '',
  调拨数量: 1,
  调拨原因: '',
  备注: '',
})

const categories = ref<Category[]>([])
const branches = ref<Branch[]>([])
const loading = ref(false)
const submitting = ref(false)

// 当前用户所属分公司
const currentBranch = computed(() => userStore.profile?.branch || '')

async function fetchOptions() {
  loading.value = true
  try {
    const [catRes, branchRes] = await Promise.all([
      getCategories().catch(() => ({ data: [] as Category[] })),
      getBranches().catch(() => ({ data: [] as Branch[] })),
    ])
    categories.value = Array.isArray(catRes.data) ? catRes.data : (catRes.data as any).results || []
    branches.value = Array.isArray(branchRes.data) ? branchRes.data : (branchRes.data as any).results || []
    // 默认调出分公司为当前用户所属分公司
    if (currentBranch.value) {
      form.value.fromBranch = currentBranch.value
    }
  } catch {
    // options loading failure is non-fatal
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!form.value.资产编号.trim()) {
    ElMessage.warning('请输入资产编号')
    return
  }
  if (!form.value.toBranch) {
    ElMessage.warning('请选择调入分公司')
    return
  }
  if (!form.value.调拨数量 || form.value.调拨数量 < 1) {
    ElMessage.warning('请输入有效数量')
    return
  }

  submitting.value = true
  try {
    await transferAsset({
      调拨日期: form.value.调拨日期 || new Date().toISOString().slice(0, 10),
      资产编号: form.value.资产编号.trim(),
      资产名称: form.value.资产名称.trim(),
      fromBranch: form.value.fromBranch || undefined,
      toBranch: form.value.toBranch || undefined,
      调拨数量: form.value.调拨数量,
      调拨原因: form.value.调拨原因,
      备注: form.value.备注,
    })
    ElMessage.success('调拨申请已提交')
    router.back()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    submitting.value = false
  }
}

function goBack() {
  router.back()
}

onMounted(() => {
  fetchOptions()
})
</script>

<template>
  <div class="submit-page">
    <!-- 头部 -->
    <div class="page-header">
      <button class="back-btn" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
      </button>
      <h1>提交调拨</h1>
      <span class="header-spacer"></span>
    </div>

    <!-- 表单 -->
    <div class="form-section">
      <div class="form-group">
        <label class="form-label">资产编号 <span class="required">*</span></label>
        <input
          v-model="form.资产编号"
          type="text"
          class="form-input"
          placeholder="请输入资产编号"
        />
      </div>

      <div class="form-group">
        <label class="form-label">资产名称</label>
        <input
          v-model="form.资产名称"
          type="text"
          class="form-input"
          placeholder="请输入资产名称"
        />
      </div>

      <div class="form-group">
        <label class="form-label">调出分公司</label>
        <select v-model="form.fromBranch" class="form-select">
          <option value="">请选择调出分公司</option>
          <option v-for="branch in branches" :key="branch.id" :value="branch.id">
            {{ branch.name }}
          </option>
        </select>
      </div>

      <div class="form-group">
        <label class="form-label">调入分公司 <span class="required">*</span></label>
        <select v-model="form.toBranch" class="form-select">
          <option value="">请选择调入分公司</option>
          <option v-for="branch in branches" :key="branch.id" :value="branch.id">
            {{ branch.name }}
          </option>
        </select>
      </div>

      <div class="form-group">
        <label class="form-label">调拨数量 <span class="required">*</span></label>
        <div class="qty-input-group">
          <button class="qty-btn" @click="form.调拨数量 = Math.max(1, form.调拨数量 - 1)">-</button>
          <input v-model.number="form.调拨数量" type="number" class="form-input qty-input" min="1" />
          <button class="qty-btn" @click="form.调拨数量++">+</button>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">调拨原因</label>
        <textarea
          v-model="form.调拨原因"
          class="form-textarea"
          placeholder="请输入调拨原因"
          rows="2"
        ></textarea>
      </div>

      <div class="form-group">
        <label class="form-label">备注</label>
        <textarea
          v-model="form.备注"
          class="form-textarea"
          placeholder="请输入备注信息"
          rows="2"
        ></textarea>
      </div>
    </div>

    <!-- 提交按钮 -->
    <div class="submit-section">
      <button class="submit-btn" @click="handleSubmit" :disabled="submitting">
        {{ submitting ? '提交中...' : '提交调拨' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.submit-page { min-height: 100vh; background: var(--color-bg-page); padding-bottom: 100px; }
.page-header { display: flex; align-items: center; justify-content: space-between; padding: var(--space-4); background: var(--color-bg-card); border-bottom: 1px solid var(--color-border); position: sticky; top: 0; z-index: 10; }
.page-header h1 { font-size: 18px; font-weight: 600; color: var(--color-text-primary); margin: 0; }
.header-spacer { width: 36px; }
.back-btn { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; background: var(--color-bg-elevated); border: none; border-radius: 50%; color: var(--color-text-secondary); cursor: pointer; }
.back-btn svg { width: 20px; height: 20px; }
.form-section { padding: var(--space-4); }
.form-group { margin-bottom: var(--space-4); }
.form-label { display: block; font-size: 14px; font-weight: 500; color: var(--color-text-primary); margin-bottom: var(--space-2); }
.required { color: var(--color-danger); }
.form-input, .form-select, .form-textarea { width: 100%; height: 44px; padding: 0 var(--space-3); border: 1px solid var(--color-border); border-radius: 10px; background: var(--color-bg-card); font-size: 15px; color: var(--color-text-primary); box-sizing: border-box; }
.form-input:focus, .form-select:focus, .form-textarea:focus { outline: none; border-color: var(--color-primary-500); }
.form-select { appearance: none; -webkit-appearance: none; background-image: url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L6 6L11 1' stroke='%23999' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 12px center; padding-right: 36px; }
.form-textarea { height: auto; padding: var(--space-3); resize: vertical; line-height: 1.5; }
.qty-input-group { display: flex; align-items: center; gap: var(--space-3); }
.qty-btn { width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; background: var(--color-bg-elevated); border: 1px solid var(--color-border); border-radius: 10px; font-size: 20px; font-weight: 500; color: var(--color-text-primary); cursor: pointer; flex-shrink: 0; }
.qty-input { text-align: center; flex: 1; }
.submit-section { position: fixed; bottom: 0; left: 0; right: 0; padding: var(--space-4); background: var(--color-bg-card); border-top: 1px solid var(--color-border); max-width: 480px; margin: 0 auto; }
.submit-btn { width: 100%; height: 48px; border: none; border-radius: 12px; background: var(--color-primary-500); color: white; font-size: 16px; font-weight: 500; cursor: pointer; }
.submit-btn:disabled { opacity: 0.5; }
</style>
