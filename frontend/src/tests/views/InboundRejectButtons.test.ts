import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import TransferDetailLayout from '@/views/transfers/components/TransferDetailLayout.vue'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}))

const baseDoc = {
  id: 't-1', 单据编号: 'TB-1', 审批状态: '待审批', action_type: 'transfer',
  调出分公司: '甲公司', 调入分公司: '乙公司',
  canOperate: false, canInboundReject: true,
  lines: [], 品项数: 0, 总数量: 0,
} as any

function mountLayout(doc: any) {
  return mount(TransferDetailLayout, {
    props: { title: '调拨详情', backPath: '/transfers/transfer', doc, type: 'transfer' as const },
    global: { stubs: { TransferLinesTable: true } },
  })
}

describe('调入方驳回入口显隐（transfer-inbound-reject）', () => {
  it('调出方视角（canOperate）显示通过/驳回，无调入方驳回', () => {
    const wrapper = mountLayout({ ...baseDoc, canOperate: true, canInboundReject: false })
    const text = wrapper.find('.detail-footer').text()
    expect(text).toContain('通过')
    expect(text).not.toContain('调入方')
    wrapper.unmount()
  })

  it('调入方视角（canOperate=false 且 canInboundReject）显示驳回（调入方）', () => {
    const wrapper = mountLayout(baseDoc)
    const footer = wrapper.find('.detail-footer')
    expect(footer.text()).toContain('驳回（调入方）')
    expect(footer.text()).not.toContain('通过')
    expect(footer.find('button').attributes('class')).toContain('btn-reject')
    wrapper.unmount()
  })

  it('非待审批或无权限时无操作按钮', () => {
    const wrapper = mountLayout({ ...baseDoc, 审批状态: '已通过', canInboundReject: false })
    expect(wrapper.find('.detail-footer button').exists()).toBe(false)
    wrapper.unmount()
  })

  it('点击调入方驳回触发 inboundReject 事件', async () => {
    const wrapper = mountLayout(baseDoc)
    await wrapper.find('.detail-footer button').trigger('click')
    expect(wrapper.emitted('inboundReject')).toHaveLength(1)
    wrapper.unmount()
  })
})
