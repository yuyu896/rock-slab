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
