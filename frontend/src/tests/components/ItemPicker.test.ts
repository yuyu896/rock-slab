import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ItemPicker from '@/components/ItemPicker.vue'

vi.mock('@/api/categories', () => ({
  getCategories: vi.fn().mockResolvedValue({
    data: {
      results: [
        { id: 'c1', 资产编号: 'NB-001', 资产名称: '笔记本', 规格: '14寸', 计量单位: '台',
          资产类目: '固定资产', 物品分类: '电脑', 管理方式: 'quantity' },
      ],
    },
  }),
}))
vi.mock('@/api/assets', () => ({
  getAssetStocks: vi.fn().mockResolvedValue({
    data: {
      results: [
        { item: 'i1', 资产编号: 'A4-001', 资产名称: 'A4纸', 规格: '500张/包', 计量单位: '包',
          资产类目: '低值易耗品', 物品分类: '办公用品', 管理方式: 'quantity', 在库数量: 12 },
        { item: 'i2', 资产编号: 'ZJ-001', 资产名称: '签字笔', 规格: '黑', 计量单位: '支',
          资产类目: '低值易耗品', 物品分类: '办公用品', 管理方式: 'consumable', 回收库数量: 0 },
      ],
    },
  }),
}))

import { getCategories } from '@/api/categories'
import { getAssetStocks } from '@/api/assets'

function state(wrapper: ReturnType<typeof mount>) {
  return (wrapper.vm as any).$.setupState
}

describe('ItemPicker 双数据源（写单表单选项收口）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('无 stockColumn 维持全量字典检索', async () => {
    const wrapper = mount(ItemPicker, { props: { modelValue: '' } })
    state(wrapper).remoteSearch('笔')
    await flushPromises()
    expect(getCategories).toHaveBeenCalledWith({ keyword: '笔', pageSize: 50 })
    expect(getAssetStocks).not.toHaveBeenCalled()
    expect(state(wrapper).options).toHaveLength(1)
    expect(state(wrapper).options[0]).toMatchObject({ id: 'c1', asset_code: 'NB-001' })
  })

  it('有 stockColumn 走台账检索并携带可用数量', async () => {
    const wrapper = mount(ItemPicker, {
      props: { modelValue: '', branch: '分公司A', stockColumn: '在库数量' },
    })
    state(wrapper).remoteSearch('纸')
    await flushPromises()
    expect(getAssetStocks).toHaveBeenCalledWith({
      branch: '分公司A', keyword: '纸', positive_column: '在库数量', pageSize: 50,
    })
    expect(getCategories).not.toHaveBeenCalled()
    expect(state(wrapper).options).toHaveLength(2)
    expect(state(wrapper).options[0]).toMatchObject({ id: 'i1', qty: 12 })
  })

  it('未选分公司时禁用且不发检索', async () => {
    const wrapper = mount(ItemPicker, {
      props: { modelValue: '', branch: '', stockColumn: '在用数量' },
    })
    expect(state(wrapper).disabled).toBe(true)
    state(wrapper).remoteSearch('纸')
    await flushPromises()
    expect(getAssetStocks).not.toHaveBeenCalled()
    expect(getCategories).not.toHaveBeenCalled()
  })

  it('excludeConsumable 剔除消耗品行（回收库来源）', async () => {
    const wrapper = mount(ItemPicker, {
      props: {
        modelValue: '', branch: '分公司A', stockColumn: '回收库数量', excludeConsumable: true,
      },
    })
    state(wrapper).remoteSearch('')
    await flushPromises()
    const codes = state(wrapper).options.map((o: any) => o.asset_code)
    expect(codes).toEqual(['A4-001']) // ZJ-001 消耗品被剔除
  })

  it('分公司变化后旧选项清空待重查', async () => {
    const wrapper = mount(ItemPicker, {
      props: { modelValue: '', branch: '分公司A', stockColumn: '在库数量' },
    })
    state(wrapper).remoteSearch('')
    await flushPromises()
    expect(state(wrapper).options).toHaveLength(2)
    await wrapper.setProps({ branch: '分公司B' })
    expect(state(wrapper).options).toHaveLength(0)
  })
})
