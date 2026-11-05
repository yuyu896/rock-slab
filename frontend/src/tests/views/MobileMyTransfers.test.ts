import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const { push, deleteTransferDraft, getTransfers, submitTransfer, withdrawTransfer, confirm, permissions } = vi.hoisted(() => ({
  push: vi.fn(),
  deleteTransferDraft: vi.fn().mockResolvedValue({ data: {} }),
  getTransfers: vi.fn(),
  submitTransfer: vi.fn().mockResolvedValue({ data: {} }),
  withdrawTransfer: vi.fn().mockResolvedValue({ data: {} }),
  confirm: vi.fn().mockResolvedValue('confirm'),
  permissions: [] as string[],
}))

vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn() }, ElMessageBox: { confirm } }))
vi.mock('@/api/transfers', () => ({ deleteTransferDraft, getTransfers, submitTransfer, withdrawTransfer }))
vi.mock('@/store/user', () => ({
  useUserStore: () => ({ can: (code: string) => permissions.includes(code) }),
}))

import MobileMyTransfers from '@/views/mobile/MyTransfers.vue'

function response(results: any[] = []) {
  return { data: { count: results.length, results } }
}

describe('MobileMyTransfers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    permissions.length = 0
    getTransfers.mockResolvedValue(response())
    confirm.mockResolvedValue('confirm')
  })

  it('编辑权限会按 mine=true 查询本人单据的可处理状态', async () => {
    permissions.push('view_assignment', 'edit_assignment', 'view_asset_ledger')
    mount(MobileMyTransfers)
    await flushPromises()
    expect(getTransfers).toHaveBeenCalledTimes(3)
    for (const [params] of getTransfers.mock.calls) {
      expect(params).toEqual(expect.objectContaining({ mine: true, page: 1, pageSize: 50 }))
      expect(params.type).toBe('assign')
      expect(['草稿', '已驳回', '待审批']).toContain(params.status)
    }
  })

  it('没有本人单据权限时不请求任何类型', async () => {
    mount(MobileMyTransfers)
    await flushPromises()
    expect(getTransfers).not.toHaveBeenCalled()
  })

  it('仅服务端允许编辑的草稿可打开移动端表单', async () => {
    permissions.push('view_assignment', 'edit_assignment', 'view_asset_ledger')
    getTransfers.mockResolvedValueOnce(response([{
      id: 'draft-1', actionType: 'assign', 审批状态: '草稿', canEditDraft: true,
      单据编号: 'LY-1', lines: [], updatedAt: '2026-10-15T10:00:00Z',
    }]))
    const wrapper = mount(MobileMyTransfers)
    await flushPromises()
    await wrapper.get('.edit-btn').trigger('click')
    expect(push).toHaveBeenCalledWith({ path: '/mobile/submit/assign', query: { id: 'draft-1' } })
  })

  it('编辑权限同时提供编辑和提交按钮', async () => {
    permissions.push('view_assignment', 'edit_assignment', 'view_asset_ledger')
    getTransfers.mockResolvedValueOnce(response([{
      id: 'draft-submit', actionType: 'assign', 审批状态: '草稿', canEditDraft: true,
      单据编号: 'LY-2', lines: [], updatedAt: '2026-10-15T10:00:00Z',
    }]))
    const wrapper = mount(MobileMyTransfers)
    await flushPromises()

    expect(wrapper.find('.edit-btn').exists()).toBe(true)
    expect(wrapper.find('.submit-btn').exists()).toBe(true)
    await wrapper.get('.submit-btn').trigger('click')
    await flushPromises()
    expect(submitTransfer).toHaveBeenCalledWith('draft-submit')
  })

  it('编辑权限可撤回本人待审批单据', async () => {
    permissions.push('view_assignment', 'edit_assignment', 'view_asset_ledger')
    getTransfers.mockResolvedValueOnce(response([{
      id: 'pending-withdraw', actionType: 'assign', 审批状态: '待审批', canWithdraw: true,
      单据编号: 'LY-3', lines: [], updatedAt: '2026-10-15T10:00:00Z',
    }]))
    const wrapper = mount(MobileMyTransfers)
    await flushPromises()
    await wrapper.findAll('[role="tab"]')[2].trigger('click')
    expect(wrapper.find('.withdraw-btn').exists()).toBe(true)
    await wrapper.get('.withdraw-btn').trigger('click')
    await flushPromises()
    expect(confirm).toHaveBeenCalled()
    expect(withdrawTransfer).toHaveBeenCalledWith('pending-withdraw')
  })

  it('删除草稿权限需要查看前置，且可删除本人草稿', async () => {
    permissions.push('delete_assignment_draft', 'view_assignment')
    getTransfers.mockResolvedValueOnce(response([{
      id: 'draft-delete', actionType: 'assign', 审批状态: '草稿', canEditDraft: true,
      单据编号: 'LY-4', lines: [], updatedAt: '2026-10-15T10:00:00Z',
    }]))
    const wrapper = mount(MobileMyTransfers)
    await flushPromises()

    expect(wrapper.find('.edit-btn').exists()).toBe(false)
    expect(wrapper.find('.delete-btn').exists()).toBe(true)
    await wrapper.get('.delete-btn').trigger('click')
    await flushPromises()

    expect(deleteTransferDraft).toHaveBeenCalledWith('draft-delete')
    expect(confirm).toHaveBeenCalled()
  })

  it('canEditDraft=false 时不显示修改或提交操作', async () => {
    permissions.push('view_purchase', 'edit_purchase', 'view_categories')
    getTransfers.mockResolvedValueOnce(response([{
      id: 'draft-2', actionType: 'purchase', 审批状态: '草稿', canEditDraft: false,
      单据编号: 'CG-2', lines: [], updatedAt: '2026-10-15T10:00:00Z',
    }]))
    const wrapper = mount(MobileMyTransfers)
    await flushPromises()
    expect(wrapper.find('.edit-btn').exists()).toBe(false)
    expect(wrapper.find('.submit-btn').exists()).toBe(false)
    expect(wrapper.text()).toContain('当前账号没有此单据的可操作权限')
  })
})
