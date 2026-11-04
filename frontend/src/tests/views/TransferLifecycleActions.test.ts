import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

const { push, deleteTransferDraft, submitTransfer, withdrawTransfer } = vi.hoisted(() => ({
  push: vi.fn(),
  deleteTransferDraft: vi.fn().mockResolvedValue({ data: {} }),
  submitTransfer: vi.fn().mockResolvedValue({ data: {} }),
  withdrawTransfer: vi.fn().mockResolvedValue({ data: {} }),
}))

vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn() },
  ElMessageBox: { confirm: vi.fn().mockResolvedValue('confirm') },
}))
vi.mock('@/store/user', () => ({
  useUserStore: () => ({ isAdmin: false, can: () => true }),
}))
vi.mock('@/api/transfers', () => ({ deleteTransferDraft, submitTransfer, withdrawTransfer }))

import TransferLifecycleActions from '@/views/transfers/components/TransferLifecycleActions.vue'

const baseDoc = { id: 't-1', 审批状态: '待审批', canWithdraw: true } as any

describe('TransferLifecycleActions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('只按服务端 canWithdraw 显示撤回并调用接口', async () => {
    const wrapper = mount(TransferLifecycleActions, {
      props: { doc: baseDoc, type: 'assign', showWithdraw: true },
    })
    expect(wrapper.text()).toContain('撤回')
    await wrapper.get('button').trigger('click')
    expect(withdrawTransfer).toHaveBeenCalledWith('t-1')
  })

  it('草稿显示提交审批和编辑入口', async () => {
    const wrapper = mount(TransferLifecycleActions, {
      props: { doc: { ...baseDoc, 审批状态: '草稿', canWithdraw: false, canEditDraft: true }, type: 'transfer' },
    })
    expect(wrapper.text()).toContain('修改草稿')
    expect(wrapper.text()).toContain('提交审批')
    await wrapper.findAll('button')[1].trigger('click')
    expect(submitTransfer).toHaveBeenCalledWith('t-1')
  })

  it('仅草稿显示删除入口，确认后调用删除接口并刷新列表', async () => {
    const wrapper = mount(TransferLifecycleActions, {
      props: {
        doc: { ...baseDoc, 单据编号: 'LY-001', 审批状态: '草稿', canWithdraw: false, canEditDraft: true },
        type: 'assign',
      },
    })

    await wrapper.get('.danger').trigger('click')

    expect(deleteTransferDraft).toHaveBeenCalledWith('t-1')
    expect(wrapper.emitted('deleted')).toHaveLength(1)
  })

  it('驳回单据跳转对应创建页继续编辑', async () => {
    const wrapper = mount(TransferLifecycleActions, {
      props: { doc: { ...baseDoc, 审批状态: '已驳回', canWithdraw: false, canEditDraft: true }, type: 'recovery' },
    })
    await wrapper.get('button').trigger('click')
    expect(push).toHaveBeenCalledWith({ path: '/transfers/recovery/create', query: { id: 't-1' } })
  })

  it('服务端未授权编辑时隐藏草稿操作', () => {
    const wrapper = mount(TransferLifecycleActions, {
      props: { doc: { ...baseDoc, 审批状态: '草稿', canWithdraw: false, canEditDraft: false }, type: 'assign' },
    })
    expect(wrapper.text()).toBe('')
  })

  it('非草稿不显示删除入口', () => {
    const wrapper = mount(TransferLifecycleActions, {
      props: { doc: { ...baseDoc, canEditDraft: true }, type: 'assign' },
    })
    expect(wrapper.find('.danger').exists()).toBe(false)
  })

  it('列表隐藏撤回入口，但不影响详情中显式启用的撤回入口', () => {
    const listWrapper = mount(TransferLifecycleActions, {
      props: { doc: baseDoc, type: 'assign' },
    })
    expect(listWrapper.text()).not.toContain('撤回')

    const detailWrapper = mount(TransferLifecycleActions, {
      props: { doc: baseDoc, type: 'assign', showWithdraw: true },
    })
    expect(detailWrapper.text()).toContain('撤回')
  })
})
