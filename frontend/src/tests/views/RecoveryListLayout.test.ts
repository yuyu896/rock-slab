import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'recovery-1' }, query: {} }),
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn(), prompt: vi.fn() },
}))

vi.mock('@/api/transfers', () => ({
  getTransfers: vi.fn(),
  getTransfer: vi.fn(),
  approveTransfer: vi.fn(),
  rejectTransfer: vi.fn(),
  importTransfers: vi.fn(),
  exportTransfers: vi.fn(),
}))

vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [] }),
}))

vi.mock('@/store/user', () => ({
  useUserStore: () => ({ can: () => true }),
}))

import { getTransfer, getTransfers } from '@/api/transfers'
import RecoveryDetail from '@/views/transfers/RecoveryDetail.vue'
import RecoveryList from '@/views/transfers/RecoveryList.vue'
import recoveryListSource from '@/views/transfers/RecoveryList.vue?raw'

const longRemark = '回收原因：' + '这是一段很长的备注，用于验证列表不会被内容撑宽。'.repeat(8)

function listStubs() {
  return {
    BasePagination: { template: '<div class="pagination-stub" />' },
    BranchFilterSelect: { template: '<div class="branch-filter-stub" />' },
  }
}

describe('回收列表长备注和固定操作列', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getTransfers).mockResolvedValue({
      data: {
        count: 1,
        results: [{
          id: 'recovery-1',
          单据编号: 'HS-001',
          调拨日期: '2026-10-15',
          调出分公司: '测试分公司',
          回收去向: 'dispose',
          品项数: 1,
          总数量: 1,
          审批状态: '待审批',
          经办人: '张三',
          备注: longRemark,
          lines: [],
        }],
      },
    } as any)
  })

  it('长备注使用受限文本容器并保留全文到 title，操作列带固定列标记', async () => {
    const wrapper = mount(RecoveryList, { global: { stubs: listStubs() } })
    await flushPromises()

    const remark = wrapper.find('.remark-text')
    expect(remark.exists()).toBe(true)
    expect(remark.text()).toBe(longRemark)
    expect(remark.attributes('title')).toBe(longRemark)
    expect(wrapper.find('th.action-column').exists()).toBe(true)
    expect(wrapper.find('td.action-column').exists()).toBe(true)
  })

  it('列表样式限制备注宽度并将操作列固定在右侧', () => {
    expect(recoveryListSource).toContain('max-width: 240px')
    expect(recoveryListSource).toContain('text-overflow: ellipsis')
    expect(recoveryListSource).toContain('position: sticky; right: 0')
    expect(recoveryListSource).toContain('.data-table tbody tr:hover td.action-column')
  })
})

describe('回收详情完整备注', () => {
  it('详情页显示完整备注，不复用列表的单行省略样式', async () => {
    vi.mocked(getTransfer).mockResolvedValue({
      data: {
        id: 'recovery-1',
        审批状态: '已通过',
        回收去向: 'dispose',
        处置方式: '报废',
        备注: longRemark,
        lines: [],
      },
    } as any)

    const wrapper = mount(RecoveryDetail, {
      global: {
        stubs: {
          TransferDetailLayout: {
            name: 'TransferDetailLayout',
            props: ['title', 'backPath', 'type', 'doc', 'loading'],
            template: '<div><slot v-if="doc" name="extra-view" :doc="doc" /></div>',
          },
        },
      },
    })
    await flushPromises()

    const remark = wrapper.find('.remark-value')
    expect(remark.exists()).toBe(true)
    expect(remark.text()).toBe(longRemark)
    expect(remark.classes()).toContain('remark-value')
  })
})
