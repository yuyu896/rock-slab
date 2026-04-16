/* 磐盘 - useTable 组合式函数 */
import { ref, reactive } from 'vue'
import type { PaginatedResponse, PaginationParams } from '@/types'

interface TableState<T> {
  data: T[]
  loading: boolean
  pagination: {
    page: number
    pageSize: number
    total: number
  }
  filters: Record<string, any>
  fetchList: () => Promise<void>
  resetFilters: () => Promise<void>
  handlePageChange: (page: number) => Promise<void>
  handleSizeChange: (size: number) => Promise<void>
}

/**
 * 封装列表页面的分页、筛选、加载逻辑
 * @param fetchFn API 请求函数，需返回 PaginatedResponse
 * @param defaultPageSize 默认每页条数
 */
export function useTable<T>(
  fetchFn: (params: PaginationParams & Record<string, any>) => Promise<{ data: PaginatedResponse<T> }>,
  defaultPageSize = 20,
): TableState<T> {
  const data = ref<T[]>([]) as any as T[]
  const loading = ref(false)
  const pagination = reactive({
    page: 1,
    pageSize: defaultPageSize,
    total: 0,
  })
  const filters = reactive<Record<string, any>>({})

  async function fetchList() {
    loading.value = true
    try {
      const { data: response } = await fetchFn({
        page: pagination.page,
        pageSize: pagination.pageSize,
        ...filters,
      })
      // 兼容 ref 包裹
      ;(data as any).value ? ((data as any).value = response.results) : (data as any).splice(0, (data as any).length, ...response.results)
      pagination.total = response.count
    } finally {
      loading.value = false
    }
  }

  async function resetFilters() {
    Object.keys(filters).forEach((key) => {
      filters[key] = undefined
    })
    pagination.page = 1
    await fetchList()
  }

  async function handlePageChange(page: number) {
    pagination.page = page
    await fetchList()
  }

  async function handleSizeChange(size: number) {
    pagination.pageSize = size
    pagination.page = 1
    await fetchList()
  }

  return {
    data: data as any,
    loading: loading as any,
    pagination,
    filters,
    fetchList,
    resetFilters,
    handlePageChange,
    handleSizeChange,
  }
}
