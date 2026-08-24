import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { computed } from 'vue'

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}))

vi.mock('@/hooks/usePermission', () => ({
  usePermission: () => ({
    canManageAssets: computed(() => true),
    can: () => true,
  }),
}))

vi.mock('@/api/assets', () => ({
  getAssetStocks: vi.fn(),
  importAssetStocks: vi.fn(),
  exportAssetStocks: vi.fn(),
  downloadAssetStockTemplate: vi.fn(),
  getFixedAssets: vi.fn(),
  getLedgerAdjustments: vi.fn(),
  createLedgerAdjustment: vi.fn(),
}))

vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [{ name: '分公司A', code: 'CS001' }] }),
}))

vi.mock('@/api/categories', () => ({
  getCategories: vi.fn().mockResolvedValue({
    data: { count: 1, results: [{ 资产类目: '固定资产' }] },
  }),
}))

import AssetSummary from '@/views/assets/AssetSummary.vue'
import SummaryImportDialog from '@/views/assets/SummaryImportDialog.vue'
import { getAssetStocks, importAssetStocks } from '@/api/assets'
import type { AssetStock } from '@/types'

const BasePaginationStub = {
  name: 'BasePagination',
  props: ['total', 'currentPage', 'pageSize'],
  emits: ['change'],
  template: '<button class="stub-go-page2" @click="$emit(\'change\', 2, 50)">page2</button>',
}

function _stock(overrides: Partial<AssetStock>): AssetStock {
  return {
    id: 's1',
    branch: 'b1',
    branchName: '分公司A',
    item: 'i1',
    资产编号: 'A-1',
    资产类目: '固定资产',
    物品分类: '办公设备',
    资产名称: '办公椅',
    规格: '标准',
    管理方式: 'quantity',
    在库数量: 7,
    在用数量: 2,
    回收库数量: 1,
    总量: 10,
    警戒线: 5,
    生效警戒线: 5,
    是否充足: true,
    ...overrides,
  } as AssetStock
}

function mountSummary() {
  return mount(AssetSummary, {
    global: {
      stubs: { BasePagination: BasePaginationStub },
    },
  })
}

describe('AssetSummary 页面（P1 台账契约）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('表头 15 列（P3 加操作列：行内调整），序号为分页连续序号', async () => {
    vi.mocked(getAssetStocks).mockResolvedValue({
      data: { count: 30, next: null, previous: null, results: [_stock({ id: 's1' }), _stock({ id: 's2' })] },
    } as any)
    const wrapper = await mountSummary()
    await flushPromises()

    const headers = wrapper.findAll('thead th').map(th => th.text())
    expect(headers).toEqual([
      '序号', '分公司', '资产编号', '资产名称', '规格', '资产类目', '管理方式',
      '在库', '在用', '回收库', '总量', '警戒线', '是否充足', '实例', '操作',
    ])

    // 第 1 页首行序号为 1，默认每页 50 条
    expect(wrapper.find('tbody tr td').text()).toBe('1')
    expect(getAssetStocks).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1, pageSize: 50 }),
    )

    // 翻到第 2 页 → 序号从 51 开始
    await wrapper.find('.stub-go-page2').trigger('click')
    await flushPromises()
    expect(getAssetStocks).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 2, pageSize: 50 }),
    )
    expect(wrapper.find('tbody tr td').text()).toBe('51')
  })

  it('四列数量直显（在库/在用/回收库/总量）', async () => {
    vi.mocked(getAssetStocks).mockResolvedValue({
      data: { count: 1, next: null, previous: null, results: [_stock({})] },
    } as any)
    const wrapper = await mountSummary()
    await flushPromises()

    const cells = wrapper.find('tbody tr').findAll('td')
    expect(cells[7].text()).toBe('7')
    expect(cells[8].text()).toBe('2')
    expect(cells[9].text()).toBe('1')
    expect(cells[10].text()).toBe('10')
  })

  it('行内唯一写操作是「调整」（开调整单），无直接改数入口（铁律 2）', async () => {
    vi.mocked(getAssetStocks).mockResolvedValue({
      data: { count: 1, next: null, previous: null, results: [_stock({})] },
    } as any)
    const wrapper = await mountSummary()
    await flushPromises()
    expect(wrapper.text()).not.toContain('新增')
    expect(wrapper.find('tbody .action-btn').exists()).toBe(false)
    expect(wrapper.find('tbody .drill-btn').text()).toBe('调整')
  })

  it('库存不足行显示「否」并以警示样式标识', async () => {
    vi.mocked(getAssetStocks).mockResolvedValue({
      data: {
        count: 2, next: null, previous: null,
        results: [_stock({ id: 's1', 是否充足: true }), _stock({ id: 's2', 是否充足: false })],
      },
    } as any)
    const wrapper = await mountSummary()
    await flushPromises()

    const badges = wrapper.findAll('.sufficient-badge')
    expect(badges[0].text()).toBe('是')
    expect(badges[0].classes()).toContain('ok')
    expect(badges[1].text()).toBe('否')
    expect(badges[1].classes()).toContain('low')
  })
})

describe('SummaryImportDialog 增量导入弹窗（两段式）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('visible=false 时不渲染（刷新页面不弹窗回归）', () => {
    const wrapper = mount(SummaryImportDialog, { props: { visible: false } })
    expect(wrapper.find('.modal-overlay').exists()).toBe(false)
  })

  function pickFile(wrapper: ReturnType<typeof mount>) {
    const input = wrapper.find('input[type="file"]')
    const file = new File(['bytes'], 'summary.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    return input.trigger('change')
  }

  it('预览展示差异清单；未确认前不产生 success', async () => {
    vi.mocked(importAssetStocks).mockResolvedValue({
      data: {
        diffs: [
          { 行号: 2, 分公司: '分公司A', 资产编号: 'A-1', 资产名称: '办公椅', 现值: 7, 导入值: 12, 变动量: 5 },
        ],
        errors: ['第3行: 资产编号 DUP-9 未在品目字典登记'],
      },
    } as any)

    const wrapper = mount(SummaryImportDialog, { props: { visible: true } })
    await pickFile(wrapper)
    await wrapper.find('.btn-secondary').trigger('click')
    await flushPromises()

    expect(importAssetStocks).toHaveBeenCalledWith(expect.any(File))
    expect(wrapper.text()).toContain('A-1')
    expect(wrapper.text()).toContain('DUP-9')
    expect(wrapper.emitted('success')).toBeFalsy()
  })

  it('确认入账以 confirm=true 再次提交并触发 success', async () => {
    vi.mocked(importAssetStocks)
      .mockResolvedValueOnce({
        data: { diffs: [{ 行号: 2, 分公司: '分公司A', 资产编号: 'A-1', 现值: 7, 导入值: 12, 变动量: 5 }], errors: [] },
      } as any)
      .mockResolvedValueOnce({ data: { applied: 1, errors: [] } } as any)

    const wrapper = mount(SummaryImportDialog, { props: { visible: true } })
    await pickFile(wrapper)
    await wrapper.find('.btn-secondary').trigger('click')
    await flushPromises()
    await wrapper.find('.btn-confirm').trigger('click')
    await flushPromises()

    expect(importAssetStocks).toHaveBeenLastCalledWith(expect.any(File), true)
    expect(wrapper.emitted('success')).toBeTruthy()
  })
})
