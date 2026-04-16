/* 磐盘 - 盘点 Store */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getInventoryTasks,
  getInventoryTask,
  createInventoryTask,
  cancelInventory,
  approveInventory,
  rejectInventory,
  recountInventory,
  getInventoryReport,
  getInventoryProgress,
  getInventoryChecks,
  startInventory,
  submitInventory,
} from '@/api/inventories'
import request, { handleApiError } from '@/utils/request'
import type {
  InventoryTask,
  InventoryReport,
  InventoryProgress,
  InventoryCheck,
  PaginatedResponse,
  PaginationParams,
} from '@/types'

export const useInventoryStore = defineStore('inventory', () => {
  const tasks = ref<InventoryTask[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentTask = ref<InventoryTask | null>(null)
  const currentReport = ref<InventoryReport | null>(null)
  const currentProgress = ref<InventoryProgress | null>(null)
  const currentChecks = ref<InventoryCheck[]>([])
  const checksTotal = ref(0)

  async function fetchTasks(params?: PaginationParams & {
    status?: string
    branchId?: string
  }) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getInventoryTasks(params)
      tasks.value = data.results
      total.value = data.count
    } catch (err) {
      error.value = handleApiError(err)
      ElMessage.error(error.value)
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(id: string) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getInventoryTask(id)
      currentTask.value = data
    } catch (err) {
      error.value = handleApiError(err)
      ElMessage.error(error.value)
    } finally {
      loading.value = false
    }
  }

  async function createTask(data: Partial<InventoryTask>) {
    const response = await createInventoryTask(data)
    return response.data
  }

  async function deleteTask(id: string) {
    await request.delete(`/inventories/${id}`)
    await fetchTasks()
  }

  async function startTask(id: string) {
    const response = await startInventory(id)
    currentTask.value = response.data
    return response.data
  }

  async function cancelTask(id: string) {
    const response = await cancelInventory(id)
    currentTask.value = response.data
    await fetchTasks()
    return response.data
  }

  async function submitTask(id: string) {
    const response = await submitInventory(id)
    currentTask.value = response.data
    return response.data
  }

  async function approveTask(id: string) {
    const response = await approveInventory(id)
    currentTask.value = response.data
    await fetchTasks()
    return response.data
  }

  async function rejectTask(id: string, reason: string) {
    const response = await rejectInventory(id, { reason })
    currentTask.value = response.data
    await fetchTasks()
    return response.data
  }

  async function recountTask(id: string) {
    const response = await recountInventory(id)
    currentTask.value = response.data
    await fetchTasks()
    return response.data
  }

  async function fetchReport(id: string) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getInventoryReport(id)
      currentReport.value = data
      return data
    } catch (err) {
      error.value = handleApiError(err)
      ElMessage.error(error.value)
    } finally {
      loading.value = false
    }
  }

  async function fetchProgress(id: string) {
    const { data } = await getInventoryProgress(id)
    currentProgress.value = data
    return data
  }

  async function fetchChecks(id: string, params?: PaginationParams) {
    const { data } = await getInventoryChecks(id, params)
    currentChecks.value = (data as PaginatedResponse<InventoryCheck>).results
    checksTotal.value = (data as PaginatedResponse<InventoryCheck>).count
    return data
  }

  return {
    tasks,
    total,
    loading,
    error,
    currentTask,
    currentReport,
    currentProgress,
    currentChecks,
    checksTotal,
    fetchTasks,
    fetchTask,
    createTask,
    deleteTask,
    startTask,
    cancelTask,
    submitTask,
    approveTask,
    rejectTask,
    recountTask,
    fetchReport,
    fetchProgress,
    fetchChecks,
  }
})
