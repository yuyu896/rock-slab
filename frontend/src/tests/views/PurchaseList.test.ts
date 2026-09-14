import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
  ElSelect: { name: 'ElSelect', props: ['modelValue', 'filterable', 'clearable', 'placeholder'], emits: ['update:modelValue', 'clear'], template: '<div class="el-select-stub" />' },
  ElOption: { name: 'ElOption', props: ['value', 'label'], template: '<div class="el-option-stub" />' },
}))
vi.mock('@/api/transfers', () => ({
  getTransfers: vi.fn().mockResolvedValue({ data: { count: 0, results: [] } }),
  exportTransfers: vi.fn(),
}))
vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [{ id: 'b-1', name: '北京分公司' }] }),
}))

import PurchaseList from '@/views/transfers/PurchaseList.vue'
import { getTransfers } from '@/api/transfers'

describe('PurchaseList 入库分公司筛选', () => {
  beforeEach(() => vi.clearAllMocks())

  it('选中分公司后请求携带 toBranch（入库分公司口径）', async () => {
    const wrapper = mount(PurchaseList, {
      global: {
        stubs: {
          BranchFilterSelect: {
            name: 'BranchFilterSelect',
            props: ['modelValue', 'options', 'allLabel'],
            emits: ['update:modelValue'],
            template: '<button class="stub-branch" @click="$emit(\'update:modelValue\', \'北京分公司\')" />',
          },
        },
      },
    })
    await flushPromises()
    await wrapper.find('.stub-branch').trigger('click')
    await flushPromises()

    const calls = vi.mocked(getTransfers).mock.calls
    const lastCall = calls[calls.length - 1]?.[0] as Record<string, unknown>
    expect(lastCall.toBranch).toBe('北京分公司')
  })
})

describe('PurchaseList 待审批置顶排序', () => {
  it('待审批在最前，其余按分公司', async () => {
    const { getTransfers } = await import('@/api/transfers')
    vi.mocked(getTransfers).mockResolvedValue({
      data: {
        count: 3, next: null, previous: null,
        results: [
          { id: 'a', 审批状态: '已入库', 调入分公司: 'A公司', 调拨日期: '2026-09-14', lines: [] } as any,
          { id: 'b', 审批状态: '待审批', 调入分公司: 'Z公司', 调拨日期: '2026-09-01', lines: [] } as any,
          { id: 'c', 审批状态: '已入库', 调入分公司: 'B公司', 调拨日期: '2026-09-13', lines: [] } as any,
        ],
      },
    } as any)
    const wrapper = mount(PurchaseList, {
      global: { stubs: { BranchFilterSelect: { template: '<div />' } } },
    })
    await flushPromises()
    const codes = wrapper.findAll('tbody tr .doc-number').map(n => n.text())
    expect(codes[0]).toBe('b')
    expect(codes[1]).toBe('a')
    expect(codes[2]).toBe('c')
  })
})
