/* 磐盘 - 资产 Store */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getAssets, getAsset } from '@/api/assets'
import { handleApiError } from '@/utils/request'
import type { Asset, PaginationParams } from '@/types'

export const useAssetStore = defineStore('asset', () => {
  const assets = ref<Asset[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentAsset = ref<Asset | null>(null)

  async function fetchAssets(params?: PaginationParams & {
    branch?: string
    category?: string
    status?: string
    keyword?: string
    ordering?: string
  }) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getAssets(params)
      assets.value = data.results
      total.value = data.count
    } catch (err) {
      error.value = handleApiError(err)
      ElMessage.error(error.value)
    } finally {
      loading.value = false
    }
  }

  async function fetchAsset(id: string) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getAsset(id)
      currentAsset.value = data
    } catch (err) {
      error.value = handleApiError(err)
      ElMessage.error(error.value)
    } finally {
      loading.value = false
    }
  }

  return {
    assets,
    total,
    loading,
    error,
    currentAsset,
    fetchAssets,
    fetchAsset,
  }
})
