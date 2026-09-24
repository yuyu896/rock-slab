import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('@/api/assets', () => ({
  getFixedAssets: vi.fn().mockResolvedValue({ data: { count: 0, next: null, previous: null, results: [] } }),
}))
vi.mock('@/utils/request', () => ({
  default: { get: vi.fn().mockResolvedValue({ data: [] }) },
}))

import InstancePicker from '@/components/InstancePicker.vue'
import { getFixedAssets } from '@/api/assets'
import request from '@/utils/request'

function makeInst(i: number) {
  return { id: `i-${i}`, 内部编号: `X-${i}`, 序列号: '', branchName: '北京分公司', 当前状态: '在库' }
}

async function mountPicker(props: Record<string, unknown> = {}) {
  const wrapper = mount(InstancePicker, {
    props: {
      itemCode: 'X', status: '在库', branchName: '北京分公司',
      modelValue: [], expanded: false, ...props,
    },
  })
  await wrapper.setProps({ expanded: true })
  await flushPromises()
  return wrapper
}

describe('InstancePicker 补全（instance-picker-completeness）', () => {
  beforeEach(() => vi.clearAllMocks())

  it('未选分公司禁用且提示，不加载', async () => {
    const wrapper = await mountPicker({ branchName: '' })
    const btn = wrapper.find('.picker-toggle')
    expect(btn.attributes('disabled')).toBeDefined()
    expect(btn.text()).toContain('请先选择所属分公司')
    expect(getFixedAssets).not.toHaveBeenCalled()
    expect(wrapper.find('.picker-panel').exists()).toBe(false)
  })

  it('搜索触发重载并携带 inner_keyword', async () => {
    const wrapper = await mountPicker()
    expect(getFixedAssets).toHaveBeenCalledWith(expect.objectContaining({ page: 1 }))
    await wrapper.find('.search-input').setValue('X-12')
    await flushPromises()
    const calls = vi.mocked(getFixedAssets).mock.calls
    const last = calls[calls.length - 1][0] as any
    expect(last.inner_keyword).toBe('X-12')
    expect(last.page).toBe(1)
  })

  it('滚动触底翻页加载下一页（破 100 截断）', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 137, next: 'http://x?page=2', previous: null, results: [makeInst(1)] },
    } as any)
    const wrapper = await mountPicker()
    const panel = wrapper.find('.picker-panel')
    const el = panel.element as HTMLElement & { scrollTop: number }
    Object.defineProperty(el, 'scrollHeight', { value: 500, configurable: true })
    Object.defineProperty(el, 'clientHeight', { value: 260, configurable: true })
    el.scrollTop = 260  // 触底（260 + 260 >= 500 - 30）
    await panel.trigger('scroll')
    await flushPromises()
    const calls = vi.mocked(getFixedAssets).mock.calls
    expect(calls.some(c => (c[0] as any).page === 2)).toBe(true)
    expect(wrapper.text()).not.toContain('共 1 台')
  })

  it('占用行置灰标注单号且不可选', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 1, next: null, previous: null, results: [makeInst(5)] },
    } as any)
    vi.mocked(request.get).mockResolvedValue({
      data: [{ instanceId: 'i-5', instanceCode: 'X-5', docNo: 'LY20260924-012', docStatus: '待审批' }],
    })
    const wrapper = await mountPicker()
    await flushPromises()
    const row = wrapper.find('.picker-row')
    expect(row.classes()).toContain('occupied')
    expect(wrapper.text()).toContain('LY20260924-012 占用')
    await row.trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })
})
