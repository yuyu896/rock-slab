<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getDepartments, createDepartment, deleteDepartment, type Department } from '@/api/departments'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePermission } from '@/hooks/usePermission'
import BasePagination from '@/components/BasePagination.vue'

const { canManageOrganizations } = usePermission()

const branches = ref<{ id: string; name: string }[]>([])
const departments = ref<Department[]>([])
const pagination = ref({ page: 1, pageSize: 50, total: 0 })
const loading = ref(false)
const filterBranch = ref('')

const newBranchId = ref('')
const newName = ref('')
const saving = ref(false)

async function fetchDepartments() {
  loading.value = true
  try {
    const { data } = await getDepartments({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      branch: filterBranch.value || undefined,
    })
    departments.value = data.results
    pagination.value.total = data.count
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!newBranchId.value || !newName.value.trim()) {
    ElMessage.warning('请选择分公司并填写部门名称')
    return
  }
  saving.value = true
  try {
    await createDepartment({ branch: newBranchId.value, name: newName.value.trim() })
    ElMessage.success('已添加')
    newName.value = ''
    await fetchDepartments()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    saving.value = false
  }
}

async function handleDelete(d: Department) {
  try {
    await ElMessageBox.confirm(`确定删除「${d.branchName} · ${d.name}」？`, '删除确认', { type: 'warning' })
    await deleteDepartment(d.id)
    ElMessage.success('已删除')
    await fetchDepartments()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

function handlePaginationChange(page: number, pageSize: number) {
  pagination.value.page = page
  pagination.value.pageSize = pageSize
  fetchDepartments()
}

onMounted(async () => {
  fetchDepartments()
  try {
    const { data } = await getBranches()
    branches.value = data.map((b: any) => ({ id: b.id, name: b.name }))
  } catch (error) {
    console.error(error)
  }
})
</script>

<template>
  <div class="dept-page page-fill">
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">部门字典</h1>
        <p class="page-desc">归属标签（分公司 × 部门名），供资产/单据表单下拉归一；不是组织树节点</p>
      </div>
    </div>

    <div v-if="canManageOrganizations" class="add-row">
      <select v-model="newBranchId" class="filter-select" aria-label="选择分公司">
        <option value="">选择分公司</option>
        <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
      </select>
      <input v-model="newName" type="text" class="filter-input" placeholder="部门名称" @keyup.enter="handleCreate" />
      <button class="btn-primary" :disabled="saving" @click="handleCreate">添加</button>
    </div>

    <div class="filter-row">
      <select v-model="filterBranch" class="filter-select" aria-label="筛选分公司" @change="pagination.page = 1; fetchDepartments()">
        <option value="">全部分公司</option>
        <option v-for="b in branches" :key="b.id" :value="b.name">{{ b.name }}</option>
      </select>
    </div>

    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>序号</th>
            <th>分公司</th>
            <th>部门名称</th>
            <th v-if="canManageOrganizations">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && departments.length === 0">
            <td :colspan="canManageOrganizations ? 4 : 3" class="empty-cell">加载中...</td>
          </tr>
          <tr v-else-if="departments.length === 0">
            <td :colspan="canManageOrganizations ? 4 : 3" class="empty-cell">暂无部门（存量部门文本可在台账迁移时归一生成）</td>
          </tr>
          <tr v-for="(d, index) in departments" :key="d.id">
            <td class="col-index">{{ (pagination.page - 1) * pagination.pageSize + index + 1 }}</td>
            <td>{{ d.branchName }}</td>
            <td>{{ d.name }}</td>
            <td v-if="canManageOrganizations">
              <button class="action-btn danger" @click="handleDelete(d)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <BasePagination
      :total="pagination.total"
      :current-page="pagination.page"
      :page-size="pagination.pageSize"
      @change="handlePaginationChange"
    />
  </div>
</template>

<style scoped>
.dept-page { max-width: 900px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-5); flex-shrink: 0; }
.header-info { display: flex; flex-direction: column; gap: var(--space-1); }
.page-title { font-size: var(--text-xl); font-weight: 600; margin: 0; }
.page-desc { font-size: var(--text-sm); color: var(--color-text-tertiary); margin: 0; }
.add-row { display: flex; gap: var(--space-3); margin-bottom: var(--space-4); }
.filter-row { display: flex; gap: var(--space-3); margin-bottom: var(--space-4); }
.filter-select { height: 38px; padding: 0 var(--space-3); min-width: 160px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); font-size: var(--text-sm); }
.filter-input { flex: 1; height: 38px; padding: 0 var(--space-3); border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); font-size: var(--text-sm); }
.btn-primary { height: 38px; padding: 0 var(--space-5); border: none; border-radius: 8px; background: var(--color-primary-500); color: #fff; cursor: pointer; font-size: var(--text-sm); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.table-container { background: var(--color-bg-card); border-radius: 12px; border: 1px solid var(--color-border); overflow: auto; flex: 1; min-height: 200px; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { background: var(--color-bg-elevated); padding: var(--space-3) var(--space-4); text-align: left; font-size: var(--text-sm); font-weight: 500; color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); }
.data-table td { padding: var(--space-3) var(--space-4); font-size: var(--text-sm); border-bottom: 1px solid var(--color-border-light); }
.col-index { width: 56px; text-align: center; color: var(--color-text-tertiary); }
.empty-cell { text-align: center; padding: var(--space-8) 0; color: var(--color-text-tertiary); }
.action-btn { border: none; background: none; cursor: pointer; font-size: var(--text-sm); color: var(--color-text-tertiary); }
.action-btn.danger { color: var(--color-danger); }
</style>
