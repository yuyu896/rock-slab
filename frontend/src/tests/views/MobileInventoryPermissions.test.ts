import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const state = vi.hoisted(() => ({
  permissions: [] as string[],
  push: vi.fn(),
  getInventoryTasks: vi.fn(),
  approveInventory: vi.fn(),
}))

vi.mock('vue-router', () => ({ useRouter: () => ({ push: state.push }) }))
vi.mock('@/store/user', () => ({
  useUserStore: () => ({ can: (code: string) => state.permissions.includes(code) }),
}))
vi.mock('@/api/inventories', () => ({
  getInventoryTasks: state.getInventoryTasks,
  approveInventory: state.approveInventory,
  rejectInventory: vi.fn(),
}))
vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() },
  ElMessageBox: { confirm: vi.fn().mockResolvedValue(true), prompt: vi.fn() },
}))

import MobileInventoryList from '@/views/mobile/InventoryList.vue'

describe('MobileInventoryList permission visibility', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    state.permissions = []
    state.getInventoryTasks.mockResolvedValue({ data: { results: [] } })
    state.approveInventory.mockResolvedValue({})
  })

  it('review-only sees only the assigned-review tab and queries pending review tasks', async () => {
    state.permissions = ['review_inventory']
    state.getInventoryTasks.mockResolvedValue({ data: { results: [{
      id: 'task-1', name: '分公司盘点', status: 'pending_review',
      createdAt: '2026-10-22', branchName: '分公司 A', checkedCount: 3, totalCount: 5,
    }] } })

    const wrapper = mount(MobileInventoryList)
    await flushPromises()

    expect(wrapper.findAll('.tab-bar button').map(button => button.text())).toEqual(['待审核'])
    expect(state.getInventoryTasks).toHaveBeenCalledWith({ status: 'pending_review', pageSize: 50 })
    expect(wrapper.find('.review-actions').exists()).toBe(true)
    expect(wrapper.find('.arrow-icon').exists()).toBe(false)
  })

  it.each(['import_inventory', 'rescan_inventory', 'view_inventory_report'])(
    '仅有 %s 时不加载移动盘点任务', async (permission) => {
      state.permissions = [permission]

      const wrapper = mount(MobileInventoryList)
      await flushPromises()

      expect(state.getInventoryTasks).not.toHaveBeenCalled()
      expect(wrapper.findAll('.tab-bar button')).toHaveLength(0)
    },
  )
})
