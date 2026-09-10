import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRouter: () => ({ replace: vi.fn() }),
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

vi.mock('@/api/inventories', () => ({
  createInventoryTask: vi.fn(),
}))
vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [{ id: 'b-1', name: '北京分公司' }] }),
}))
vi.mock('@/api/categories', () => ({
  getCategories: vi.fn().mockResolvedValue({ data: { results: [] } }),
}))
vi.mock('@/api/departments', () => ({
  getDepartmentOptions: vi.fn(),
}))

import InventoryTaskCreate from '@/views/inventory/InventoryTaskCreate.vue'
import { createInventoryTask } from '@/api/inventories'

async function _mount() {
  const wrapper = mount(InventoryTaskCreate)
  await flushPromises()
  return wrapper
}

describe('InventoryTaskCreate 实例盘去部门', () => {
  beforeEach(() => vi.clearAllMocks())

  it('页面无盘点部门下拉；实例盘 radio 文案为全公司口径', async () => {
    const wrapper = await _mount()
    expect(wrapper.text()).not.toContain('盘点部门')
    expect(wrapper.text()).toContain('实例盘点（逐台核对全公司在用资产）')
    await wrapper.find('input[type=radio][value=instance]').setValue()
    expect(wrapper.text()).toContain('全公司「在用」实例')
  })

  it('选实例盘提交：payload 含 kind=instance 且不含 department', async () => {
    const wrapper = await _mount()
    await wrapper.find('input[type=radio][value=instance]').setValue()
    const selects = wrapper.findAll('select')
    await selects[0].setValue('b-1') // 分公司
    const nameInput = wrapper.find('input[type=text]')
    await nameInput.setValue('全公司实例盘')

    await wrapper.find('button.btn-primary').trigger('click')
    await flushPromises()

    expect(createInventoryTask).toHaveBeenCalledTimes(1)
    const payload = vi.mocked(createInventoryTask).mock.calls[0][0] as Record<string, unknown>
    expect(payload.kind).toBe('instance')
    expect(payload).not.toHaveProperty('department')
  })
})
