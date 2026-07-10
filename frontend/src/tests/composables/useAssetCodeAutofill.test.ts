import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/api/categories', () => ({
  lookupCategoryByCode: vi.fn(),
}))

import { useAssetCodeAutofill } from '@/composables/useAssetCodeAutofill'
import { lookupCategoryByCode } from '@/api/categories'

describe('useAssetCodeAutofill', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('命中时返回分类数据并清空 notFoundCode（且对编号做 trim）', async () => {
    const data = { 资产名称: '笔记本', 资产类目: '固定资产', 物品分类: '办公设备', 计量单位: '台' }
    vi.mocked(lookupCategoryByCode).mockResolvedValue({ data } as any)

    const { lookupByCode, notFoundCode } = useAssetCodeAutofill()
    const result = await lookupByCode('  A-001  ')

    expect(result).toEqual(data)
    expect(notFoundCode.value).toBeNull()
    expect(lookupCategoryByCode).toHaveBeenCalledWith('A-001')
  })

  it('未命中(404)时返回 null 并记录 notFoundCode', async () => {
    vi.mocked(lookupCategoryByCode).mockRejectedValue(new Error('404'))

    const { lookupByCode, notFoundCode } = useAssetCodeAutofill()
    const result = await lookupByCode('NOPE-999')

    expect(result).toBeNull()
    expect(notFoundCode.value).toBe('NOPE-999')
  })

  it('空编号不发起请求并清空 notFoundCode', async () => {
    const { lookupByCode, notFoundCode } = useAssetCodeAutofill()
    notFoundCode.value = 'OLD'
    const result = await lookupByCode('   ')

    expect(result).toBeNull()
    expect(notFoundCode.value).toBeNull()
    expect(lookupCategoryByCode).not.toHaveBeenCalled()
  })
})
