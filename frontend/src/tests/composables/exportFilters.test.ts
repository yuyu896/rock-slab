import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { computed, defineComponent } from 'vue'

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/utils/importTemplate', () => ({
  generateTransferTemplate: vi.fn(),
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

vi.mock('@/api/transfers', () => ({
  getTransfers: vi.fn(),
  getTransfer: vi.fn(),
  approveTransfer: vi.fn(),
  rejectTransfer: vi.fn(),
  importTransfers: vi.fn(),
  exportTransfers: vi.fn(),
}))

vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({
    data: [
      { id: 'b1', name: '杭州分公司', code: 'HZ001' },
      { id: 'b2', name: '上海分公司', code: 'SH001' },
    ],
  }),
}))

vi.mock('@/api/categories', () => ({
  getCategories: vi.fn().mockResolvedValue({
    data: { count: 1, results: [{ id: 'c1', 资产类目: '固定资产', 物品分类: '办公设备' }] },
  }),
}))

vi.mock('@/hooks/usePermission', () => ({
  usePermission: () => ({ canManageAssets: computed(() => true) }),
}))

import { useTransferList } from '@/composables/useTransferList'
import AssetList from '@/views/AssetList.vue'
import FixedAssetList from '@/views/FixedAssetList.vue'
import { exportAssets, exportFixedAssets } from '@/api/assets'
import { exportTransfers, getTransfers } from '@/api/transfers'

const emptyPage = { data: { count: 0, next: null, previous: null, results: [] } }

function stubObjectUrl() {
  ;(URL as any).createObjectURL = vi.fn(() => 'blob:mock')
  ;(URL as any).revokeObjectURL = vi.fn()
}

function findButtonByText(wrapper: ReturnType<typeof mount>, text: string) {
  return wrapper.findAll('button').find(b => b.text().includes(text))!
}

beforeEach(() => {
  vi.clearAllMocks()
  stubObjectUrl()
  vi.mocked(getTransfers).mockResolvedValue(emptyPage as any)
  vi.mocked(exportTransfers).mockResolvedValue({ data: new Blob(['x']) } as any)
  vi.mocked(exportAssets).mockResolvedValue({ data: new Blob(['x']) } as any)
  vi.mocked(exportFixedAssets).mockResolvedValue({ data: new Blob(['x']) } as any)
})

describe('useTransferList 导出透传全部筛选', () => {
  it('回收列表：type/fromBranch/toBranch/status/keyword 全部携带', async () => {
    const wrapper = mount(defineComponent({
      setup() {
        const state = useTransferList('recovery')
        return { state }
      },
      template: '<div/>',
    }))
    await flushPromises()

    // VTU 的 vm 类型对嵌套 ref 的解包声明与运行时不一致，这里以运行时为准（filters 是 Ref）
    const state = wrapper.vm.state as any
    state.filters.value.fromBranch = '杭州分公司'
    state.filters.value.toBranch = '上海分公司'
    state.filters.value.status = '已通过'
    state.filters.value.keyword = 'A-1'
    await state.handleExport()

    expect(exportTransfers).toHaveBeenCalledWith({
      type: 'recovery',
      fromBranch: '杭州分公司',
      toBranch: '上海分公司',
      status: '已通过',
      keyword: 'A-1',
    })
  })
})

describe('资产明细导出透传全部筛选', () => {
  it('branch/category/status/keyword 全部携带', async () => {
    const wrapper = mount(AssetList, { shallow: true })
    await flushPromises()

    await wrapper.find('input[aria-label="搜索资产"]').setValue('笔记本')
    const selects = wrapper.findAll('select')
    await selects[0].setValue('杭州分公司')   // 分公司
    await selects[1].setValue('固定资产')      // 资产类目
    await selects[2].setValue('在库')          // 状态
    await findButtonByText(wrapper, '导出').trigger('click')
    await flushPromises()

    expect(exportAssets).toHaveBeenCalledWith({
      branch: '杭州分公司',
      category: '固定资产',
      status: '在库',
      keyword: '笔记本',
    })
  })
})

describe('固定资产导出透传全部筛选', () => {
  it('branch/status/keyword/资产名称 全部携带', async () => {
    const wrapper = mount(FixedAssetList, { shallow: true })
    await flushPromises()

    await wrapper.find('input[placeholder^="搜索资产编号"]').setValue('SN-1')
    await wrapper.find('input[placeholder="资产名称"]').setValue('打印机')
    const selects = wrapper.findAll('select')
    await selects[0].setValue('杭州分公司')
    await selects[1].setValue('在库')
    await findButtonByText(wrapper, '导出').trigger('click')
    await flushPromises()

    expect(exportFixedAssets).toHaveBeenCalledWith({
      branch: '杭州分公司',
      status: '在库',
      keyword: 'SN-1',
      资产名称: '打印机',
    })
  })
})
