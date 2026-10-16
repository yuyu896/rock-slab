import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

const { push, submitTransfer, withdrawTransfer } = vi.hoisted(() => ({
  push: vi.fn(),
  submitTransfer: vi.fn().mockResolvedValue({ data: {} }),
  withdrawTransfer: vi.fn().mockResolvedValue({ data: {} }),
}))

vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn() },
  ElMessageBox: { confirm: vi.fn().mockResolvedValue('confirm') },
}))
vi.mock('@/api/transfers', () => ({ submitTransfer, withdrawTransfer }))

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

  it('hides withdraw by default and shows it only when enabled on details', () => {
    const listWrapper = mount(TransferLifecycleActions, {
      props: { doc: baseDoc, type: 'assign' },
    })
    expect(listWrapper.find('.lifecycle-btn.warning').exists()).toBe(false)

    const detailWrapper = mount(TransferLifecycleActions, {
      props: { doc: baseDoc, type: 'assign', showWithdraw: true },
    })
    expect(detailWrapper.find('.lifecycle-btn.warning').exists()).toBe(true)
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
})
