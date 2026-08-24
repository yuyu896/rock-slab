import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { computed, defineComponent } from 'vue'

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ query: {} }),
}))

vi.mock('@/utils/importTemplate', () => ({
  generateTransferTemplate: vi.fn(),
}))

vi.mock('@/api/assets', () => ({
  getAssetStocks: vi.fn(),
  exportAssetStocks: vi.fn(),
  getFixedAssets: vi.fn(),
  getFixedAsset: vi.fn(),
  supplementFixedAsset: vi.fn(),
  getFixedAssetTimeline: vi.fn(),
  exportFixedAssets: vi.fn(),
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
  usePermission: () => ({
    canManageAssets: computed(() => true),
    can: () => true,
  }),
}))

import { useTransferList } from '@/composables/useTransferList'
import FixedAssetList from '@/views/FixedAssetList.vue'
import { exportFixedAssets } from '@/api/assets'
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


describe('固定资产实例导出透传全部筛选', () => {
  it('branch/status/keyword/pending_serial 全部携带', async () => {
    const wrapper = mount(FixedAssetList, { shallow: true })
    await flushPromises()

    await wrapper.find('input[placeholder^="搜索内部编号"]').setValue('NB-1')
    const selects = wrapper.findAll('select')
    await selects[0].setValue('杭州分公司')
    await selects[1].setValue('在库')
    await wrapper.find('input[type="checkbox"]').setValue(true)
    await findButtonByText(wrapper, '导出').trigger('click')
    await flushPromises()

    expect(exportFixedAssets).toHaveBeenCalledWith({
      branch: '杭州分公司',
      status: '在库',
      keyword: 'NB-1',
      pending_serial: '1',
    })
  })
})
