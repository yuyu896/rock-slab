import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { computed } from 'vue'

const permState = { canManageAssets: true }

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/api/transfers', () => ({
  recoverAsset: vi.fn(),
  getTransfers: vi.fn().mockResolvedValue({
    data: { count: 0, next: null, previous: null, results: [] },
  }),
}))

vi.mock('@/api/assets', () => ({
  getAssets: vi.fn(),
  updateAsset: vi.fn(),
  deleteAsset: vi.fn(),
  batchDeleteAssets: vi.fn(),
  exportAssets: vi.fn(),
  getFixedAssets: vi.fn(),
  getFixedAsset: vi.fn(),
  supplementFixedAsset: vi.fn(),
  getFixedAssetTimeline: vi.fn(),
  exportFixedAssets: vi.fn(),
}))

vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [] }),
}))

vi.mock('@/api/categories', () => ({
  getCategories: vi.fn().mockResolvedValue({ data: { count: 0, results: [] } }),
  lookupCategoryByCode: vi.fn().mockResolvedValue({
    data: { id: 'cat-1', 资产名称: '办公椅', 资产类目: '固定资产', 物品分类: '办公设备', 计量单位: '把', 警戒线: null },
  }),
}))

vi.mock('@/hooks/usePermission', () => ({
  usePermission: () => ({ canManageAssets: computed(() => permState.canManageAssets) }),
}))

import RecoveryDialog from '@/views/assets/RecoveryDialog.vue'
import { recoverAsset } from '@/api/transfers'
import type { FixedAsset } from '@/types'

const fixedRow = {
  id: 'f1', 内部编号: 'A-1-3', 当前状态: '在用', 序列号: 'SN-9',
  item: 'cat-1', itemCode: 'A-1', itemName: '办公椅', itemSpec: '标准',
  branchName: '分公司A', 使用人: '张三', departmentName: '仓库',
} as unknown as FixedAsset

function mountDialog(item: FixedAsset) {
  return mount(RecoveryDialog, {
    props: { visible: true, mode: 'fixed', item },
  })
}

describe('RecoveryDialog 行内回收', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(recoverAsset).mockResolvedValue({} as any)
  })

  it('固定资产模式：数量固定 1，提交携带实例引用（档案保留）', async () => {
    const wrapper = mountDialog(fixedRow)

    const qtyInput = wrapper.find('input[type="number"]')
    expect((qtyInput.element as HTMLInputElement).disabled).toBe(true)

    await wrapper.find('select').setValue('闲置回收')
    await wrapper.find('.btn-confirm').trigger('click')

    expect(recoverAsset).toHaveBeenCalledWith(expect.objectContaining({
      immediate: true,
      调出分公司: '分公司A',
      items: [expect.objectContaining({ item: 'cat-1', 数量: 1, instances: ['f1'] })],
    }))
  })
})

