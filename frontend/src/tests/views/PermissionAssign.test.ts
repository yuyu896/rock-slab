import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import PermissionAssign from '@/views/admin/PermissionAssign.vue'

const api = vi.hoisted(() => ({
  getUsers: vi.fn(),
  updateUser: vi.fn(),
  getRegions: vi.fn(),
  updateRegion: vi.fn(),
  getBranches: vi.fn(),
  updateBranch: vi.fn(),
  getTeams: vi.fn(),
  updateTeam: vi.fn(),
  createManagementScope: vi.fn(),
  deleteManagementScope: vi.fn(),
  getManagementScopes: vi.fn(),
  createOperationGrant: vi.fn(),
  deleteOperationGrant: vi.fn(),
  getOperationGrants: vi.fn(),
  getOperationCatalog: vi.fn(),
  getPositionTemplates: vi.fn(),
  getEffectivePermissions: vi.fn(),
}))

vi.mock('@/api/users', () => ({ getUsers: api.getUsers, updateUser: api.updateUser }))
vi.mock('@/api/regions', () => ({ getRegions: api.getRegions, updateRegion: api.updateRegion }))
vi.mock('@/api/branches', () => ({ getBranches: api.getBranches, updateBranch: api.updateBranch }))
vi.mock('@/api/teams', () => ({ getTeams: api.getTeams, updateTeam: api.updateTeam }))
vi.mock('@/api/permissions', () => ({
  createManagementScope: api.createManagementScope,
  deleteManagementScope: api.deleteManagementScope,
  getManagementScopes: api.getManagementScopes,
  createOperationGrant: api.createOperationGrant,
  deleteOperationGrant: api.deleteOperationGrant,
  getOperationGrants: api.getOperationGrants,
  getOperationCatalog: api.getOperationCatalog,
  getPositionTemplates: api.getPositionTemplates,
  getEffectivePermissions: api.getEffectivePermissions,
}))

const SelectStub = defineComponent({
  props: { modelValue: { type: String, default: '' } },
  emits: ['update:modelValue'],
  setup(_, { emit }) {
    const onChange = (event: Event) => emit('update:modelValue', (event.target as HTMLSelectElement).value)
    return { onChange }
  },
  template: '<select :value="modelValue" @change="onChange"><slot /></select>',
})

const OptionStub = defineComponent({
  props: { value: String, label: String },
  template: '<option :value="value">{{ label }}</option>',
})

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(r => { resolve = r })
  return { promise, resolve }
}

function mountPage() {
  return mount(PermissionAssign, {
    global: { stubs: { ElSelect: SelectStub, ElOption: OptionStub } },
  })
}

beforeEach(() => {
  vi.resetAllMocks()
  api.getUsers.mockResolvedValue({ data: [
    { id: 'manager-a', name: '员工甲', phone: '100', role: 'manager' },
    { id: 'manager-b', name: '员工乙', phone: '101', role: 'manager' },
    { id: 'admin', name: '系统管理员', phone: '102', role: 'admin' },
  ] })
  api.getOperationCatalog.mockResolvedValue({ data: [
    { code: 'approve_transfer', label: '审批资产流转' },
  ] })
  api.getPositionTemplates.mockResolvedValue({ data: [
    { role: 'manager', label: '分公司行政', scopeType: 'branch', operations: [], allOperations: false },
    { role: 'admin', label: '系统管理员', scopeType: 'all', operations: [], allOperations: true },
  ] })
  api.getRegions.mockResolvedValue({ data: [] })
  api.getBranches.mockResolvedValue({ data: [] })
  api.getTeams.mockResolvedValue({ data: [] })
  api.getManagementScopes.mockResolvedValue({ data: [] })
  api.getOperationGrants.mockResolvedValue({ data: [] })
  api.getEffectivePermissions.mockResolvedValue({ data: [] })
})

describe('PermissionAssign 当前权限显示', () => {
  it('管理员内置全部权限时将权限复选框显示为选中', async () => {
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.find('select.user-select').setValue('admin')
    await flushPromises()

    expect((wrapper.find('input[type="checkbox"]').element as HTMLInputElement).checked).toBe(true)
    expect((wrapper.find('input[type="checkbox"]').element as HTMLInputElement).disabled).toBe(true)
    wrapper.unmount()
  })

  it('快速切换员工时忽略较晚返回的旧员工授权', async () => {
    const firstUserGrants = deferred<{ data: { id: string; user: string; code: string }[] }>()
    api.getOperationGrants.mockImplementation(({ user }: { user: string }) =>
      user === 'manager-a' ? firstUserGrants.promise : Promise.resolve({ data: [] }),
    )

    const wrapper = mountPage()
    await flushPromises()
    const selector = wrapper.find('select.user-select')
    await selector.setValue('manager-a')
    await selector.setValue('manager-b')
    await flushPromises()

    firstUserGrants.resolve({
      data: [{ id: 'grant-a', user: 'manager-a', code: 'approve_transfer' }],
    })
    await flushPromises()

    expect((wrapper.find('input[type="checkbox"]').element as HTMLInputElement).checked).toBe(false)
    wrapper.unmount()
  })
})
