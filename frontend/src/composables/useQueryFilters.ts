import { watch, type Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

type Filters = Record<string, unknown>

interface QueryFilterOptions {
  /** 数组型字段：query 逗号分隔序列化 */
  arrayKeys?: string[]
  /** 布尔型字段：query '1' 为真（假值不写入） */
  boolKeys?: string[]
}

/** 列表筛选与页码的路由 query 持久化（query 为唯一持久层，组件 ref 为运行时镜像）。
 *  须在页面 fetch-watch 注册之前调用：恢复发生在 setup 期、先于 watch 注册，
 *  使 immediate/非 immediate 的 fetch 路径都只拉取一次且页码不被重置。 */
export function useQueryFilters(
  filters: Ref<Filters>,
  pagination?: Ref<{ page: number } | number>,
  options: QueryFilterOptions = {},
) {
  const route = useRoute()
  const router = useRouter()
  const arrayKeys = new Set(options.arrayKeys ?? [])
  const boolKeys = new Set(options.boolKeys ?? [])
  const filterKeys = Object.keys(filters.value)
  const getPage = () => (typeof pagination?.value === 'number' ? pagination.value : pagination?.value.page)
  const setPage = (n: number) => {
    if (!pagination) return
    if (typeof pagination.value === 'number') pagination.value = n
    else pagination.value.page = n
  }

  const first = (key: string): string | undefined => {
    const raw = route.query[key]
    const v = Array.isArray(raw) ? raw[0] : raw
    return v == null || v === '' ? undefined : String(v)
  }

  // init：从 query 恢复；未知键忽略、无法解析的值保持默认（脏 query 容错）
  filterKeys.forEach((key) => {
    const raw = first(key)
    if (raw === undefined) return
    if (arrayKeys.has(key)) filters.value[key] = raw.split(',').filter(Boolean)
    else if (boolKeys.has(key)) filters.value[key] = raw === '1'
    else if (typeof filters.value[key] === 'string') filters.value[key] = raw
  })
  const pageRaw = parseInt(first('page') ?? '', 10)
  if (Number.isFinite(pageRaw) && pageRaw > 0) setPage(pageRaw)

  // sync：筛选/页码变更 → router.replace（不产生历史记录；仅含有值键，空值键移除）
  function syncQuery() {
    const query: Record<string, string> = {}
    filterKeys.forEach((key) => {
      const v = filters.value[key]
      if (arrayKeys.has(key)) {
        if (Array.isArray(v) && v.length) query[key] = v.join(',')
      } else if (boolKeys.has(key)) {
        if (v === true) query[key] = '1'
      } else if (v) {
        query[key] = String(v)
      }
    })
    if ((getPage() ?? 1) > 1) query.page = String(getPage())
    Promise.resolve(router.replace({ query })).catch(() => {})
  }

  watch(filters, syncQuery, { deep: true })
  watch(() => getPage(), syncQuery)
}
