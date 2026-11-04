import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const { grants } = vi.hoisted(() => ({ grants: new Set<string>() }))

vi.mock('@/store/user', () => ({
  useUserStore: () => ({ can: (code: string) => grants.has(code) }),
}))

vi.mock('@/composables/useQueryFilters', () => ({
  useQueryFilters: vi.fn(),
}))

vi.mock('@/api/transfers', () => ({
  getRecoveryLedger: vi.fn().mockResolvedValue({
    data: {
      count: 1,
      results: [{
        日期: '2026-10-26', 单据编号: 'HS-001', 分公司: '测试分公司',
        品目编号: 'NB-001', 品目名称: '笔记本', 数量: 1,
        内部编号: 'NB-001-1', 实例ID: 'instance-1',
      }],
      disposal_income: 0,
    },
  }),
  exportRecoveryLedger: vi.fn(),
}))

vi.mock('@/api/assets', () => ({
  getFixedAsset: vi.fn(),
  getFixedAssetTimeline: vi.fn(),
}))

vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [] }),
}))

import RecoveryLedger from '@/views/transfers/RecoveryLedger.vue'
import { getFixedAsset, getFixedAssetTimeline } from '@/api/assets'

describe('物资处置台账实例详情权限', () => {
  beforeEach(() => {
    grants.clear()
    grants.add('view_recovery_ledger')
    vi.clearAllMocks()
  })

  it('只有台账查看权时显示编号，但不提供需要实例档案权限的详情入口', async () => {
    const wrapper = mount(RecoveryLedger, {
      global: { stubs: { BasePagination: true, BranchFilterSelect: true } },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('NB-001-1')
    expect(wrapper.find('.asset-link').exists()).toBe(false)
    expect(getFixedAsset).not.toHaveBeenCalled()
    expect(getFixedAssetTimeline).not.toHaveBeenCalled()
  })

  it('同时有实例档案查看权时提供详情入口', async () => {
    grants.add('view_instances')
    const wrapper = mount(RecoveryLedger, {
      global: { stubs: { BasePagination: true, BranchFilterSelect: true } },
    })
    await flushPromises()

    expect(wrapper.find('.asset-link').exists()).toBe(true)
  })
})
