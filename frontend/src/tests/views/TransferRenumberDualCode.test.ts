import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

const push = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))

import TransferLinesTable from '@/views/transfers/components/TransferLinesTable.vue'

const baseLine: any = {
  id: 'l-1', 行号: 1, itemCode: 'A-a00007', itemName: '笔记本电脑',
  managementType: 'instance', 数量: 2, unit: '台',
  instances: [
    { id: 'i-1', code: 'A-a00007-NB032-102', 前编号: 'A-a00007-NB018-18' },
    { id: 'i-2', code: 'A-a00007-NB032-103', 前编号: '' },
  ],
}

describe('调拨详情双编号展示', () => {
  beforeEach(() => push.mockClear())

  it('有前编号的实例显示「前编号 → 当前编号」', () => {
    const wrapper = mount(TransferLinesTable, {
      props: { lines: [baseLine], type: 'transfer' as any },
    })
    const links = wrapper.findAll('.inst-link')
    expect(links[0].text()).toBe('A-a00007-NB018-18 → A-a00007-NB032-102')
    expect(links[1].text()).toBe('A-a00007-NB032-103')
  })

  it('点击跳转用当前编号（新号查生平）', async () => {
    const wrapper = mount(TransferLinesTable, {
      props: { lines: [baseLine], type: 'transfer' as any },
    })
    await wrapper.findAll('.inst-link')[0].trigger('click')
    expect(push).toHaveBeenCalledWith({ path: '/fixed-assets', query: { keyword: 'A-a00007-NB032-102' } })
  })
})
