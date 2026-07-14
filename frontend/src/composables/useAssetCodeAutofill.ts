/* 磐盘 - 资产编号失焦反查分类（新增表单复用） */
import { ref } from 'vue'
import { lookupCategoryByCode } from '@/api/categories'

export interface AssetCodeLookupResult {
  资产名称: string
  资产类目: string
  物品分类: string
  计量单位: string
  警戒线: number | null
}

/**
 * 按「资产编号」反查资产分类，供新增表单在编号失焦时自动带出名称/类目/分类。
 * - 命中：返回分类数据，notFoundCode 置空。
 * - 未命中（404）或出错：返回 null，notFoundCode 记录该编号，供表单内联提示。
 */
export function useAssetCodeAutofill() {
  const loading = ref(false)
  const notFoundCode = ref<string | null>(null)

  async function lookupByCode(code: string): Promise<AssetCodeLookupResult | null> {
    const trimmed = (code || '').trim()
    if (!trimmed) {
      notFoundCode.value = null
      return null
    }
    loading.value = true
    try {
      const { data } = await lookupCategoryByCode(trimmed)
      notFoundCode.value = null
      return data
    } catch {
      notFoundCode.value = trimmed
      return null
    } finally {
      loading.value = false
    }
  }

  return { loading, notFoundCode, lookupByCode }
}
