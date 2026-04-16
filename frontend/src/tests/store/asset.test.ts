import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/assets', () => ({
  getAssets: vi.fn(),
  getAsset: vi.fn(),
}))

import { useAssetStore } from '@/store/asset'
import * as assetsApi from '@/api/assets'

describe('Asset Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('fetchAssets', () => {
    it('populates assets and total on success', async () => {
      const mockData = {
        results: [
          { id: '1', 资产名称: 'Test Asset 1' },
          { id: '2', 资产名称: 'Test Asset 2' },
        ],
        count: 2,
      }
      vi.mocked(assetsApi.getAssets).mockResolvedValue({ data: mockData } as any)

      const store = useAssetStore()
      await store.fetchAssets()

      expect(store.assets).toHaveLength(2)
      expect(store.total).toBe(2)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('sets error on failure', async () => {
      vi.mocked(assetsApi.getAssets).mockRejectedValue({
        response: { data: { detail: 'Server error' } },
      })

      const store = useAssetStore()
      await store.fetchAssets()

      expect(store.assets).toHaveLength(0)
      expect(store.error).toBe('Server error')
      expect(store.loading).toBe(false)
    })
  })
})
