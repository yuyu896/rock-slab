import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { computed } from 'vue'

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}))

vi.mock('@/hooks/usePermission', () => ({
  usePermission: () => ({
    canManageCategories: computed(() => true),
    can: () => true,
  }),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/api/categories', () => ({
  getCategories: vi.fn(),
  deleteCategory: vi.fn(),
  exportCategories: vi.fn(),
}))

import Category from '@/views/Category.vue'
import { getCategories, exportCategories } from '@/api/categories'
import type { Category as CategoryType } from '@/types'

function _item(overrides: Partial<CategoryType>): CategoryType {
  return {
    id: 'c1',
    资产类目: '电子设备',
    物品分类: '手机',
    资产名称: 'iPhone',
    资产编号: 'CAT-001',
    规格: '',
    管理方式: 'quantity',
    是否租用: false,
    默认供应商: '',
    计量单位: '台',
    警戒线: 5,
    备注: '',
    ...overrides,
  } as CategoryType
}

function mountPage() {
  return mount(Category)
}

describe('Category 品目页（筛选与序号）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('表头首列为序号，序号为分页连续序号', async () => {
    vi.mocked(getCategories).mockResolvedValue({
      data: { count: 120, results: [_item({ id: 'c1' }), _item({ id: 'c2' })] },
    } as any)
    const wrapper = await mountPage()
    await flushPromises()

    const headers = wrapper.findAll('thead th').map(th => th.text())
    expect(headers[0]).toBe('序号')
    expect(headers).toContain('管理方式')

    // 第 1 页首行序号为 1，默认每页 50 条
    expect(wrapper.find('tbody tr td').text()).toBe('1')

    // 翻到第 2 页 → 序号从 51 开始
    const page2 = wrapper.findAll('.page-btn').find(b => b.text() === '2')
    expect(page2).toBeTruthy()
    await page2!.trigger('click')
    await flushPromises()
    expect(getCategories).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 2, pageSize: 50 }),
    )
    expect(wrapper.find('tbody tr td').text()).toBe('51')
  })

  it('管理方式筛选下拉三档，选择后透传列表接口', async () => {
    vi.mocked(getCategories).mockResolvedValue({
      data: { count: 2, results: [_item({ id: 'c1' })] },
    } as any)
    const wrapper = await mountPage()
    await flushPromises()

    const selects = wrapper.findAll('select.filter-select')
    const mgmtSelect = selects[selects.length - 1]
    const options = mgmtSelect.findAll('option').map(o => o.text())
    expect(options).toEqual(['全部管理方式', '数量管理', '实例管理', '消耗品'])

    await mgmtSelect.setValue('consumable')
    await flushPromises()
    expect(getCategories).toHaveBeenLastCalledWith(
      expect.objectContaining({ 管理方式: 'consumable', page: 1 }),
    )
  })

  it('导出透传全部四项筛选', async () => {
    vi.mocked(getCategories).mockResolvedValue({
      data: { count: 1, results: [_item({ id: 'c1' })] },
    } as any)
    const wrapper = await mountPage()
    await flushPromises()

    const selects = wrapper.findAll('select.filter-select')
    await selects[0].setValue('电子设备') // 资产类目
    await selects[1].setValue('手机') // 物品分类
    await selects[2].setValue('consumable') // 管理方式
    const keywordInput = wrapper.find('input.filter-input')
    await keywordInput.setValue('iPhone')

    const exportBtn = wrapper.findAll('button').find(b => b.text().includes('导出'))
    await exportBtn!.trigger('click')
    expect(exportCategories).toHaveBeenCalledWith(
      expect.objectContaining({
        资产类目: '电子设备',
        物品分类: '手机',
        管理方式: 'consumable',
        keyword: 'iPhone',
      }),
    )
  })
})
