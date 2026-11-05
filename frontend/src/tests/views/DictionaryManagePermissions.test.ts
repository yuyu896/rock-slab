import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const permissionState = vi.hoisted(() => ({ codes: [] as string[] }))

vi.mock('@/hooks/usePermission', () => ({
  usePermission: () => ({
    can: (code: string) => permissionState.codes.includes(code),
  }),
}))

vi.mock('@/api/departments', () => ({
  getDepartments: vi.fn().mockResolvedValue({ data: { count: 1, results: [{ id: 'd1', name: '行政部' }] } }),
  createDepartment: vi.fn(),
  updateDepartment: vi.fn(),
  deleteDepartment: vi.fn(),
}))

vi.mock('@/api/suppliers', () => ({
  getSuppliers: vi.fn().mockResolvedValue({ data: { count: 1, results: [{ id: 's1', name: '供应商甲', 联系人: '', 电话: '' }] } }),
  createSupplier: vi.fn(),
  updateSupplier: vi.fn(),
  deleteSupplier: vi.fn(),
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}))

import DepartmentManage from '@/views/DepartmentManage.vue'
import SupplierManage from '@/views/SupplierManage.vue'

describe('字典维护页面权限', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    permissionState.codes = []
  })

  it.each([
    ['部门', DepartmentManage, 'view_departments', 'edit_departments'],
    ['供应商', SupplierManage, 'view_suppliers', 'edit_suppliers'],
  ])('%s新增、编辑和删除统一由编辑权限控制，且依赖查看权限', async (_label, component, viewCode, editCode) => {
    permissionState.codes = [editCode]
    const withoutView = mount(component as any)
    await flushPromises()

    expect(withoutView.find('.add-row').exists()).toBe(false)
    expect(withoutView.find('table').exists()).toBe(false)
    expect(withoutView.find('.permission-state').exists()).toBe(false)
    expect(withoutView.text()).toContain('没有查看')

    permissionState.codes = [viewCode, editCode]
    const withEdit = mount(component as any)
    await flushPromises()

    expect(withEdit.find('.add-row').exists()).toBe(true)
    expect(withEdit.find('button').text()).not.toBe('')
    expect(withEdit.text()).toContain('编辑')
    expect(withEdit.text()).toContain('删除')
  })
})
