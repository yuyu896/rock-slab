import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const { push, getTransfers, submitTransfer } = vi.hoisted(() => ({
  push: vi.fn(),
  getTransfers: vi.fn(),
  submitTransfer: vi.fn().mockResolvedValue({ data: {} }),
}))

vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn() } }))
vi.mock('@/api/transfers', () => ({ getTransfers, submitTransfer }))

import MobileMyTransfers from '@/views/mobile/MyTransfers.vue'

function response(results: any[] = []) {
  return { data: { count: results.length, results } }
}

describe('MobileMyTransfers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getTransfers.mockResolvedValue(response())
  })

  it('按 mine=true 查询已有移动端单据类型的草稿和驳回单', async () => {
    mount(MobileMyTransfers)
    await flushPromises()
    expect(getTransfers).toHaveBeenCalledTimes(6)
    for (const [params] of getTransfers.mock.calls) {
      expect(params).toEqual(expect.objectContaining({ mine: true, page: 1, pageSize: 50 }))
      expect(['purchase', 'assign', 'transfer']).toContain(params.type)
      expect(['草稿', '已驳回']).toContain(params.status)
    }
  })

  it('仅服务端允许编辑的草稿可打开移动端表单', async () => {
    getTransfers.mockResolvedValueOnce(response([{
      id: 'draft-1', actionType: 'assign', 审批状态: '草稿', canEditDraft: true,
      单据编号: 'LY-1', lines: [], updatedAt: '2026-10-15T10:00:00Z',
    }]))
    const wrapper = mount(MobileMyTransfers)
    await flushPromises()
    await wrapper.get('.edit-btn').trigger('click')
    expect(push).toHaveBeenCalledWith({ path: '/mobile/submit/assign', query: { id: 'draft-1' } })
  })

  it('canEditDraft=false 时不显示修改或提交操作', async () => {
    getTransfers.mockResolvedValueOnce(response([{
      id: 'draft-2', actionType: 'purchase', 审批状态: '草稿', canEditDraft: false,
      单据编号: 'CG-2', lines: [], updatedAt: '2026-10-15T10:00:00Z',
    }]))
    const wrapper = mount(MobileMyTransfers)
    await flushPromises()
    expect(wrapper.find('.edit-btn').exists()).toBe(false)
    expect(wrapper.find('.submit-btn').exists()).toBe(false)
    expect(wrapper.text()).toContain('当前账号不可编辑')
  })
})
