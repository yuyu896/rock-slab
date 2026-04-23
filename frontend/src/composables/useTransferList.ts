import { ref, computed, onMounted, watch } from 'vue'
import {
  getTransfers, getTransfer,
  approveTransfer as approveTransferApi, rejectTransfer as rejectTransferApi,
  importTransfers, exportTransfers
} from '@/api/transfers'
import { generateTransferTemplate } from '@/utils/importTemplate'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { APPROVAL_STATUS_OPTIONS, APPROVAL_STATUS_COLORS } from '@/constants'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Transfer } from '@/types'

// 流转类型元数据
export const TRANSFER_TYPES = {
  purchase: { label: '采购入库', color: { bg: 'oklch(0.92 0.08 340)', color: 'oklch(0.45 0.12 340)' } },
  assign: { label: '领用出库', color: { bg: 'var(--color-primary-50)', color: 'var(--color-primary-600)' } },
  transfer: { label: '调拨', color: { bg: 'oklch(0.92 0.06 240)', color: 'oklch(0.45 0.12 250)' } },
} as const

export type TransferType = keyof typeof TRANSFER_TYPES

export function useTransferList(type: TransferType) {
  const { label: typeLabel, color: typeColor } = TRANSFER_TYPES[type]

  // 筛选
  const filters = ref({
    status: '',
    fromBranch: '',
    toBranch: '',
    keyword: ''
  })

  // 分页
  const pagination = ref({ page: 1, pageSize: 20, total: 0 })
  const loading = ref(false)
  const transfers = ref<Transfer[]>([])
  const branchOptions = ref<{ value: string; label: string }[]>([{ value: '', label: '全部分公司' }])
  const statusOptions = APPROVAL_STATUS_OPTIONS

  const getStatusStyle = (status: string) => {
    return APPROVAL_STATUS_COLORS[status as keyof typeof APPROVAL_STATUS_COLORS] || { bg: 'var(--color-bg-elevated)', color: 'var(--color-text-secondary)' }
  }

  const stats = computed(() => ({
    total: pagination.value.total,
    pending: transfers.value.filter(t => t.审批状态 === '待审批').length,
    approved: transfers.value.filter(t => t.审批状态 === '已通过').length,
    rejected: transfers.value.filter(t => t.审批状态 === '已驳回').length,
    warehoused: transfers.value.filter(t => t.审批状态 === '已入库').length,
  }))

  async function fetchTransfers() {
    loading.value = true
    try {
      const { data } = await getTransfers({
        page: pagination.value.page,
        pageSize: pagination.value.pageSize,
        status: filters.value.status || undefined,
        fromBranch: filters.value.fromBranch || undefined,
        toBranch: filters.value.toBranch || undefined,
        type,
      })
      transfers.value = data.results
      pagination.value.total = data.count
    } catch (error) {
      ElMessage.error(handleApiError(error))
    } finally {
      loading.value = false
    }
  }

  async function fetchBranches() {
    try {
      const { data } = await getBranches()
      branchOptions.value = [
        { value: '', label: '全部分公司' },
        ...data.map((b: any) => ({ value: b.id, label: b.name }))
      ]
    } catch (error) {
      console.error('Failed to fetch branches:', error)
    }
  }

  // 详情弹窗
  const showDetailModal = ref(false)
  const detailItem = ref<Transfer | null>(null)
  const detailLoading = ref(false)

  async function viewDetail(item: Transfer) {
    detailItem.value = item
    showDetailModal.value = true
    if (!item.资产名称) {
      detailLoading.value = true
      try {
        const { data } = await getTransfer(item.id)
        detailItem.value = data
      } catch { /* use cached */ } finally {
        detailLoading.value = false
      }
    }
  }

  // 审批
  async function handleApprove(item: Transfer) {
    try {
      await ElMessageBox.confirm('确定通过此申请？', '审批确认', { type: 'info' })
      await approveTransferApi(item.id, { approved: true })
      ElMessage.success('审批通过')
      await fetchTransfers()
    } catch (error) {
      if (error !== 'cancel') ElMessage.error(handleApiError(error))
    }
  }

  async function handleReject(item: Transfer) {
    try {
      const { value } = await ElMessageBox.prompt('请输入驳回原因', '驳回确认', {
        confirmButtonText: '确定驳回',
        cancelButtonText: '取消',
        inputValidator: (v: string) => (v && v.trim() ? true : '请输入驳回原因'),
      })
      await rejectTransferApi(item.id, { reason: value })
      ElMessage.success('已驳回')
      await fetchTransfers()
    } catch (error) {
      if (error !== 'cancel') ElMessage.error(handleApiError(error))
    }
  }

  // 批量导入
  const showImportModal = ref(false)
  const importLoading = ref(false)
  const importResult = ref<{ imported: number; errors: string[] } | null>(null)

  function openImportModal() {
    importResult.value = null
    importLoading.value = false
    showImportModal.value = true
  }

  function handleDownloadTemplate() {
    const templateConfig: Record<TransferType, { filename: string }> = {
      purchase: { filename: '采购入库导入模板' },
      assign: { filename: '领用出库导入模板' },
      transfer: { filename: '调拨导入模板' },
    }
    const { filename } = templateConfig[type]
    generateTransferTemplate(filename, type)
  }

  async function handleImportFile(event: Event) {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return

    const ext = file.name.split('.').pop()?.toLowerCase()
    if (ext !== 'xlsx' && ext !== 'xls') {
      ElMessage.warning('请上传 Excel 文件（.xlsx 或 .xls）')
      input.value = ''
      return
    }

    importLoading.value = true
    importResult.value = null
    try {
      const { data } = await importTransfers(file, type)
      importResult.value = data
      if (data.errors.length === 0) {
        ElMessage.success(`成功导入 ${data.imported} 条流转记录`)
        setTimeout(() => {
          showImportModal.value = false
          fetchTransfers()
        }, 1200)
      }
    } catch (error) {
      ElMessage.error(handleApiError(error))
    } finally {
      importLoading.value = false
      input.value = ''
    }
  }

  // 导出
  async function handleExport() {
    try {
      const params: Record<string, string> = { type }
      if (filters.value.fromBranch) params.fromBranch = filters.value.fromBranch
      if (filters.value.toBranch) params.toBranch = filters.value.toBranch
      if (filters.value.status) params.status = filters.value.status
      const { data } = await exportTransfers(params)
      const blob = new Blob([data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${typeLabel}_${new Date().toISOString().slice(0, 10)}.xlsx`
      link.click()
      URL.revokeObjectURL(url)
      ElMessage.success('导出成功')
    } catch (error) {
      ElMessage.error(handleApiError(error))
    }
  }

  function resetFilters() {
    filters.value = { status: '', fromBranch: '', toBranch: '', keyword: '' }
    pagination.value.page = 1
    fetchTransfers()
  }

  watch(filters, () => {
    pagination.value.page = 1
    fetchTransfers()
  }, { deep: true })

  onMounted(() => {
    fetchTransfers()
    fetchBranches()
  })

  return {
    type,
    typeLabel,
    typeColor,
    filters,
    pagination,
    loading,
    transfers,
    branchOptions,
    statusOptions,
    stats,
    getStatusStyle,
    fetchTransfers,
    resetFilters,
    // 详情
    showDetailModal,
    detailItem,
    detailLoading,
    viewDetail,
    // 审批
    handleApprove,
    handleReject,
    // 批量导入
    showImportModal,
    importLoading,
    importResult,
    openImportModal,
    handleDownloadTemplate,
    handleImportFile,
    // 导出
    handleExport,
  }
}
