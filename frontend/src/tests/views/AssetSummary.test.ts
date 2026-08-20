import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { computed } from 'vue'

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}))

vi.mock('@/hooks/usePermission', () => ({
  usePermission: () => ({ canManageAssets: computed(() => true) }),
}))

vi.mock('@/api/assets', () => ({
  getAssetStocks: vi.fn(),
  createAssetStock: vi.fn(),
  updateAssetStock: vi.fn(),
  deleteAssetStock: vi.fn(),
  importAssetStocks: vi.fn(),
  exportAssetStocks: vi.fn(),
  downloadAssetStockTemplate: vi.fn(),
  createAsset: vi.fn(),
  createFixedAsset: vi.fn(),
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
import SummaryFillDialog from '@/views/assets/SummaryFillDialog.vue'
import SummaryImportDialog from '@/views/assets/SummaryImportDialog.vue'
import { getAssetStocks, importAssetStocks } from '@/api/assets'
import { createAsset, createFixedAsset } from '@/api/assets'
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
    分公司: '分公司A',
    资产编号: 'A-1',
    资产类目: '固定资产',
    物品分类: '办公设备',
    资产名称: '办公椅',
    规格: '标准',
    数量: 10,
    警戒线: 5,
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

describe('AssetSummary 页面（库存台账）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('表头 10 列按约定顺序展示，序号为分页连续序号', async () => {
    vi.mocked(getAssetStocks).mockResolvedValue({
      data: { count: 30, next: null, previous: null, results: [_stock({ id: 's1' }), _stock({ id: 's2' })] },
    } as any)
    const wrapper = await mountSummary()
    await flushPromises()

    const headers = wrapper.findAll('thead th').map(th => th.text())
    expect(headers).toEqual([
      '序号', '分公司', '资产编号', '资产类目', '物品分类',
      '资产名称', '数量', '规格', '警戒线', '是否充足', '操作',
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
    const firstIndex = wrapper.find('tbody tr td').text()
    expect(firstIndex).toBe('51')
  })

  it('库存不足行显示「否」并以警示样式标识', async () => {
    vi.mocked(getAssetStocks).mockResolvedValue({
      data: {
        count: 2, next: null, previous: null,
        results: [_stock({ id: 's1', 是否充足: true }), _stock({ id: 's2', 数量: 2, 警戒线: 5, 是否充足: false })],
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

describe('SummaryFillDialog 填入弹窗', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  function mountFill(stock: AssetStock) {
    return mount(SummaryFillDialog, {
      props: { visible: true, stock },
    })
  }

  it('预填台账行字段，提交填入资产明细（携带警戒线与分公司）', async () => {
    const wrapper = mountFill(_stock({}))
    // 预填信息可见
    expect(wrapper.text()).toContain('分公司A')
    expect(wrapper.text()).toContain('A-1')
    expect(wrapper.text()).toContain('办公椅')

    await wrapper.find('input[list]').setValue('仓库')
    await wrapper.find('.btn-confirm').trigger('click')

    expect(createAsset).toHaveBeenCalledWith(expect.objectContaining({
      分公司: '分公司A',
      资产编号: 'A-1',
      警戒线: 5,
      所属部门: '仓库',
      数量: 1,
    }))
    expect(createFixedAsset).not.toHaveBeenCalled()
  })

  it('切换到固定资产：序列号必填，提交调 createFixedAsset', async () => {
    const wrapper = mountFill(_stock({}))

    await wrapper.findAll('.target-btn')[1].trigger('click')
    // 序列号为空提交 → 拦截
    await wrapper.find('.btn-confirm').trigger('click')
    expect(createFixedAsset).not.toHaveBeenCalled()

    const serial = wrapper.find('input[placeholder="请输入序列号"]')
    await serial.setValue('SN-001')
    await wrapper.find('.btn-confirm').trigger('click')

    expect(createFixedAsset).toHaveBeenCalledWith(expect.objectContaining({
      分公司: '分公司A',
      资产编号: 'A-1',
      序列号: 'SN-001',
      数量: 1,
    }))
  })
})

describe('SummaryImportDialog 导入弹窗', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('导入失败行错误逐条展示，成功部分触发 success', async () => {
    vi.mocked(importAssetStocks).mockResolvedValue({
      data: { imported: 1, errors: ['第2行：分公司「分公司A」下资产编号 DUP-1 已存在，请编辑该行'] },
    } as any)

    const wrapper = mount(SummaryImportDialog, { props: { visible: true } })
    const input = wrapper.find('input[type="file"]')
    const file = new File(['bytes'], 'summary.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')

    expect(importAssetStocks).toHaveBeenCalled()
    expect(wrapper.text()).toContain('成功导入 1 条')
    expect(wrapper.text()).toContain('DUP-1')
    expect(wrapper.emitted('success')).toBeTruthy()
  })
})
