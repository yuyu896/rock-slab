import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn(), prompt: vi.fn() },
  ElSelect: { name: 'ElSelect', props: ['modelValue', 'multiple', 'filterable', 'clearable', 'placeholder', 'collapseTags', 'collapseTagsTooltip'], template: '<div class="el-select-stub" />' },
  ElOption: { name: 'ElOption', props: ['value', 'label'], template: '<div class="el-option-stub" />' },
}))

vi.mock('@/api/transfers', () => ({
  getTransfers: vi.fn().mockResolvedValue({ data: { count: 0, results: [] } }),
  approveTransfer: vi.fn(),
  rejectTransfer: vi.fn(),
  importTransfers: vi.fn(),
  exportTransfers: vi.fn(),
}))

vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [] }),
}))
vi.mock('@/store/user', () => ({ useUserStore: () => ({ can: () => true }) }))

import BranchFilterSelect from '@/components/BranchFilterSelect.vue'
import RecoveryList from '@/views/transfers/RecoveryList.vue'

/** 回归：回收单页曾漏 import BranchFilterSelect，Vue 静默跳过未解析组件导致分公司筛选栏消失 */
describe('回收单列表分公司筛选', () => {
  it('分公司筛选组件已解析并渲染（绑定 fromBranch，空数组=不过滤）', async () => {
    const wrapper = mount(RecoveryList)
    await flushPromises()
    const branch = wrapper.findComponent(BranchFilterSelect)
    expect(branch.exists()).toBe(true)
    expect(branch.props('modelValue')).toEqual([])
    wrapper.unmount()
  })
})
