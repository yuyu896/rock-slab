import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TransferDetailLayout from '@/views/transfers/components/TransferDetailLayout.vue'
import type { TransferDocument } from '@/types'

function makeDoc(overrides: Partial<TransferDocument> = {}): TransferDocument {
  return {
    id: 't1',
    单据编号: 'TR-001',
    调拨日期: '2026-01-15',
    调出分公司: '分公司A',
    调入分公司: '分公司B',
    审批状态: '待审批',
    创建人: '张三',
    lines: [],
    createdAt: '2026-01-15T10:00:00',
    updatedAt: '2026-01-15T10:00:00',
    ...overrides,
  } as TransferDocument
}

function mountLayout(doc: TransferDocument | null) {
  return mount(TransferDetailLayout, {
    props: { title: '调拨详情', backPath: '/transfers/transfer', type: 'transfer', doc },
    global: { stubs: { teleport: true } },
  })
}

describe('TransferDetailLayout 调拨单调入方只读（修订 3.1）', () => {
  it('待审批且可操作时显示通过/驳回按钮', () => {
    const wrapper = mountLayout(makeDoc({ canOperate: true }))
    expect(wrapper.find('.btn-approve').exists()).toBe(true)
    expect(wrapper.find('.btn-reject').exists()).toBe(true)
  })

  it('canOperate=false（调入方视角）隐藏通过/驳回，详情仍可看', () => {
    const wrapper = mountLayout(makeDoc({ canOperate: false }))
    expect(wrapper.find('.btn-approve').exists()).toBe(false)
    expect(wrapper.find('.btn-reject').exists()).toBe(false)
    expect(wrapper.text()).toContain('TR-001')
  })

  it('canOperate 缺省（兼容旧数据/非调拨类型）按可操作处理', () => {
    const wrapper = mountLayout(makeDoc({}))
    expect(wrapper.find('.btn-approve').exists()).toBe(true)
  })

  it('非待审批状态不显示操作按钮', () => {
    const wrapper = mountLayout(makeDoc({ 审批状态: '已通过' }))
    expect(wrapper.find('.btn-approve').exists()).toBe(false)
  })
})
