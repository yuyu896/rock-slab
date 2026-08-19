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
  updateFixedAsset: vi.fn(),
  deleteFixedAsset: vi.fn(),
  batchDeleteFixedAssets: vi.fn(),
  importFixedAssets: vi.fn(),
  exportFixedAssets: vi.fn(),
  downloadFixedAssetTemplate: vi.fn(),
  createFixedAsset: vi.fn(),
}))

vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [] }),
}))

vi.mock('@/api/categories', () => ({
  getCategories: vi.fn().mockResolvedValue({ data: { count: 0, results: [] } }),
}))

vi.mock('@/hooks/usePermission', () => ({
  usePermission: () => ({ canManageAssets: computed(() => permState.canManageAssets) }),
}))

import RecoveryDialog from '@/views/assets/RecoveryDialog.vue'
import { recoverAsset } from '@/api/transfers'
import type { Asset, FixedAsset } from '@/types'

const assetRow = {
  id: 'a1', 序号: 1, 分公司: '分公司A', 分公司编号: 'CS001',
  资产编号: 'A-1', 资产类目: '固定资产', 物品分类: '办公设备',
  资产名称: '办公椅', 规格: '标准', 数量: 5, 所属部门: '行政部',
  当前状态: '在库', 是否租用: false,
} as unknown as Asset

const fixedRow = {
  id: 'f1', 内部编号: 'A-1-3', 资产编号: 'A-1', 资产类目: '固定资产',
  物品分类: '办公设备', 资产名称: '办公椅', 规格: '标准', 数量: 1,
  分公司: '分公司A', 所属部门: '仓库', 序列号: 'SN-9',
} as unknown as FixedAsset

function mountDialog(mode: 'asset' | 'fixed', item: Asset | FixedAsset) {
  return mount(RecoveryDialog, {
    props: { visible: true, mode, item },
  })
}

describe('RecoveryDialog 行内回收', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(recoverAsset).mockResolvedValue({} as any)
  })

  it('资产明细模式：数量受该行数量上限约束，提交携带 immediate 与调出部门', async () => {
    const wrapper = mountDialog('asset', assetRow)

    const qtyInput = wrapper.find('input[type="number"]')
    expect(qtyInput.attributes('max')).toBe('5')

    await wrapper.find('select').setValue('报废回收')
    await qtyInput.setValue(3)
    await wrapper.find('.btn-confirm').trigger('click')

    expect(recoverAsset).toHaveBeenCalledWith(expect.objectContaining({
      immediate: true,
      资产编号: 'A-1',
      调拨数量: 3,
      调出分公司: '分公司A',
      调出部门: '行政部',
      回收分类: '报废回收',
      固定资产内部编号: '',
    }))
    expect(wrapper.emitted('success')).toBeTruthy()
  })

  it('资产明细模式：数量超上限被拦截', async () => {
    const wrapper = mountDialog('asset', assetRow)
    await wrapper.find('select').setValue('报废回收')
    await wrapper.find('input[type="number"]').setValue(9)
    await wrapper.find('.btn-confirm').trigger('click')

    expect(recoverAsset).not.toHaveBeenCalled()
  })

  it('固定资产模式：数量固定 1，提交携带内部编号', async () => {
    const wrapper = mountDialog('fixed', fixedRow)

    const qtyInput = wrapper.find('input[type="number"]')
    expect((qtyInput.element as HTMLInputElement).disabled).toBe(true)

    await wrapper.find('select').setValue('闲置回收')
    await wrapper.find('.btn-confirm').trigger('click')

    expect(recoverAsset).toHaveBeenCalledWith(expect.objectContaining({
      immediate: true,
      调拨数量: 1,
      固定资产内部编号: 'A-1-3',
    }))
  })
})

describe('行内回收按钮可见性（canManageAssets）', () => {
  async function mountList(canManage: boolean) {
    permState.canManageAssets = canManage
    const { default: AssetList } = await import('@/views/AssetList.vue')
    const { getAssets } = await import('@/api/assets')
    vi.mocked(getAssets).mockResolvedValue({
      data: { count: 1, next: null, previous: null, results: [assetRow] },
    } as any)
    const wrapper = mount(AssetList, { shallow: true })
    await flushPromises()
    return wrapper
  }

  it('持 manage_assets 权限时显示「回收」按钮', async () => {
    const wrapper = await mountList(true)
    expect(wrapper.find('button[title="回收"]').exists()).toBe(true)
  })

  it('无权限时不显示「回收」按钮', async () => {
    const wrapper = await mountList(false)
    expect(wrapper.find('button[title="回收"]').exists()).toBe(false)
  })
})
