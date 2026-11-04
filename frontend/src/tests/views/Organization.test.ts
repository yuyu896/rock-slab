import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const permissions = vi.hoisted(() => ({ codes: [] as string[] }))
const ui = vi.hoisted(() => ({ confirm: vi.fn() }))

const api = vi.hoisted(() => ({
  getUsers: vi.fn(),
  getUserDeletePreview: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
  getRegions: vi.fn(),
  createRegion: vi.fn(),
  updateRegion: vi.fn(),
  deleteRegion: vi.fn(),
  getBranches: vi.fn(),
  createBranch: vi.fn(),
  updateBranch: vi.fn(),
  deleteBranch: vi.fn(),
  getTeams: vi.fn(),
  createTeam: vi.fn(),
  updateTeam: vi.fn(),
  deleteTeam: vi.fn(),
  getCompany: vi.fn(),
  updateCompany: vi.fn(),
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn() },
  ElMessageBox: { confirm: ui.confirm },
}))

vi.mock('@/api/users', () => ({
  getUsers: api.getUsers,
  getUserDeletePreview: api.getUserDeletePreview,
  createUser: api.createUser,
  updateUser: api.updateUser,
  deleteUser: api.deleteUser,
}))
vi.mock('@/api/regions', () => ({
  getRegions: api.getRegions,
  createRegion: api.createRegion,
  updateRegion: api.updateRegion,
  deleteRegion: api.deleteRegion,
}))
vi.mock('@/api/branches', () => ({
  getBranches: api.getBranches,
  createBranch: api.createBranch,
  updateBranch: api.updateBranch,
  deleteBranch: api.deleteBranch,
}))
vi.mock('@/api/teams', () => ({
  getTeams: api.getTeams,
  createTeam: api.createTeam,
  updateTeam: api.updateTeam,
  deleteTeam: api.deleteTeam,
}))
vi.mock('@/api/company', () => ({ getCompany: api.getCompany, updateCompany: api.updateCompany }))
vi.mock('@/hooks/usePermission', () => ({
  usePermission: () => ({ can: (code: string) => permissions.codes.includes(code) }),
}))

import Organization from '@/views/Organization.vue'

beforeEach(() => {
  vi.resetAllMocks()
  ui.confirm.mockResolvedValue(undefined)
  permissions.codes = ['view_organizations', 'view_users', 'edit_organizations']
  api.getCompany.mockResolvedValue({ data: { id: 'company-1', name: 'Company' } })
  api.getRegions.mockResolvedValue({ data: [{ id: 'region-1', name: 'Region', code: 'RG', canManage: true }] })
  api.getTeams.mockResolvedValue({ data: [{ id: 'team-1', name: 'Team', region: 'region-1', canManage: true }] })
  api.getBranches.mockResolvedValue({
    data: [{ id: 'branch-1', name: 'Branch', code: 'BR001', team: 'team-1', status: 'active' }],
  })
  api.getUsers.mockResolvedValue({ data: [] })
  api.getUserDeletePreview.mockResolvedValue({ data: { responsibilities: [] } })
})

describe('Organization branch edit dialog', () => {
  it('closes the dialog when cancel is clicked', async () => {
    const wrapper = mount(Organization)
    await flushPromises()

    await wrapper.find('.region-label').trigger('click')
    await wrapper.find('.team-label').trigger('click')
    await wrapper.find('.branch-label').trigger('click')
    await wrapper.find('.header-actions button.action-btn').trigger('click')
    expect(wrapper.find('.modal-mask').exists()).toBe(true)

    await wrapper.find('.modal-footer .action-btn').trigger('click')
    expect(wrapper.find('.modal-mask').exists()).toBe(false)
    wrapper.unmount()
  })

  it('shows organization edit controls only when the matching operation is granted', async () => {
    permissions.codes = ['view_organizations', 'view_users', 'create_organizations']
    const wrapper = mount(Organization)
    await flushPromises()

    await wrapper.find('.region-label').trigger('click')
    await wrapper.find('.team-label').trigger('click')

    expect(wrapper.text()).not.toContain('+ 分公司')
    await wrapper.find('.branch-label').trigger('click')
    expect(wrapper.text()).not.toContain('编辑分公司')
    expect(wrapper.text()).not.toContain('删除节点')
    wrapper.unmount()
  })
})

describe('employee and organization view prerequisites', () => {
  it('loads scoped employee and branch options when view and edit are granted', async () => {
    permissions.codes = ['view_users', 'edit_users']
    api.getUsers.mockResolvedValue({ data: [{
      id: 'user-1', name: '可维护员工', phone: '13800000000', role: 'leader',
      status: 'active', branch: 'branch-1', branchName: 'Branch',
    }] })

    const wrapper = mount(Organization)
    await flushPromises()

    expect(api.getUsers).toHaveBeenCalledWith()
    expect(api.getBranches).toHaveBeenCalledWith({ scope: 'write' })
    expect(api.getRegions).not.toHaveBeenCalled()
    expect(api.getTeams).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('可维护员工')
    expect(wrapper.text()).toContain('Branch')

    await wrapper.find('td.clickable').trigger('click')
    expect(wrapper.find('.employee-form-page').exists()).toBe(true)
    expect(wrapper.find('.employee-form-page select option[value="branch-1"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('does not expose employee actions for a standalone legacy delete grant', async () => {
    permissions.codes = ['delete_users']
    const wrapper = mount(Organization)
    await flushPromises()

    expect(api.getUsers).not.toHaveBeenCalled()
    expect(api.getBranches).not.toHaveBeenCalled()
    expect(wrapper.text()).not.toContain('删除')
    wrapper.unmount()
  })

  it('does not expose employee editing without its view permission', async () => {
    permissions.codes = ['edit_users']

    const wrapper = mount(Organization)
    await flushPromises()

    expect(api.getUsers).not.toHaveBeenCalled()
    expect(wrapper.text()).not.toContain('创建员工')
    wrapper.unmount()
  })

  it('loads only scoped organization tree options for organization editors', async () => {
    permissions.codes = ['view_organizations', 'edit_organizations']
    api.getCompany.mockResolvedValue({ data: { id: 'company-1', name: 'Limited Company' } })
    api.getRegions.mockResolvedValue({ data: [{
      id: 'region-1', name: 'Region', code: 'RG', status: 'active', canManage: false,
    }] })
    api.getTeams.mockResolvedValue({ data: [{
      id: 'team-1', name: 'Team', region: 'region-1', status: 'active', canManage: false,
    }] })

    const wrapper = mount(Organization)
    await flushPromises()

    expect(api.getCompany).toHaveBeenCalledWith({ scope: 'tree' })
    expect(api.getRegions).toHaveBeenCalledWith()
    expect(api.getTeams).toHaveBeenCalledWith()
    expect(api.getBranches).toHaveBeenCalledWith()
    expect(api.getUsers).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Limited Company')

    await wrapper.find('.region-label').trigger('click')
    expect(wrapper.find('.header-actions').text()).not.toContain('编辑区域')
    wrapper.unmount()
  })

  it('shows group-name editing only for an editor with full organization scope', async () => {
    permissions.codes = ['view_organizations', 'edit_organizations']
    api.getCompany.mockResolvedValue({ data: {
      id: 'company-1', name: 'Full Company', can_create_region: true,
    } })

    const wrapper = mount(Organization)
    await flushPromises()

    await wrapper.find('.group-label').trigger('click')
    expect(wrapper.find('.header-actions').text()).toContain('编辑集团')
    wrapper.unmount()
  })

  it('requires a successor for each managed organization before deleting an employee', async () => {
    permissions.codes = ['view_users', 'edit_users']
    api.getUsers.mockResolvedValue({ data: [{
      id: 'user-1', name: '待删除员工', phone: '13800000000', role: 'manager',
      status: 'active', branch: 'branch-1', branchName: 'Branch',
    }] })
    api.getUserDeletePreview.mockResolvedValue({ data: {
      user: { id: 'user-1', name: '待删除员工' },
      responsibilities: [{
        key: 'branch:branch-1', node_type: 'branch', type: '分公司负责人', id: 'branch-1', name: 'Branch', role: 'manager',
        candidates: [{ id: 'successor-1', name: '接任员工' }],
      }],
    } })

    const wrapper = mount(Organization)
    await flushPromises()
    await wrapper.find('.employee-table .row-btn.danger').trigger('click')
    await flushPromises()

    expect(api.getUserDeletePreview).toHaveBeenCalledWith('user-1')
    expect(wrapper.text()).toContain('请先为其负责的组织节点指定在职接任人')
    expect(api.deleteUser).not.toHaveBeenCalled()
    const confirm = wrapper.find('.employee-delete-modal .modal-footer .action-btn.danger')
    expect((confirm.element as HTMLButtonElement).disabled).toBe(true)

    await wrapper.find('.employee-delete-modal select').setValue('successor-1')
    expect((confirm.element as HTMLButtonElement).disabled).toBe(false)
    await confirm.trigger('click')
    await flushPromises()

    expect(api.deleteUser).toHaveBeenCalledWith('user-1', [{
      node_type: 'branch', node_id: 'branch-1', user_id: 'successor-1',
    }], [], [])
    wrapper.unmount()
  })

  it('blocks deletion when a responsible node has no eligible successor', async () => {
    permissions.codes = ['view_users', 'edit_users']
    api.getUsers.mockResolvedValue({ data: [{
      id: 'user-1', name: '待删除员工', phone: '13800000000', role: 'manager',
      status: 'active', branch: 'branch-1', branchName: 'Branch',
    }] })
    api.getUserDeletePreview.mockResolvedValue({ data: {
      user: { id: 'user-1', name: '待删除员工' },
      responsibilities: [{
        key: 'branch:branch-1', node_type: 'branch', type: '分公司负责人', id: 'branch-1', name: 'Branch', role: 'manager',
        candidates: [],
      }],
    } })

    const wrapper = mount(Organization)
    await flushPromises()
    await wrapper.find('.employee-table .row-btn.danger').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('该节点没有符合条件的在职接任人')
    expect((wrapper.find('.employee-delete-modal .modal-footer .action-btn.danger').element as HTMLButtonElement).disabled).toBe(true)
    expect(api.deleteUser).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('requires review of legacy drafts and sends only selected drafts for deletion', async () => {
    permissions.codes = ['view_users', 'edit_users']
    api.getUsers.mockResolvedValue({ data: [{
      id: 'user-1', name: 'Employee to delete', phone: '13800000000', role: 'manager',
      status: 'active', branch: 'branch-1', branchName: 'Branch',
    }] })
    api.getUserDeletePreview.mockResolvedValue({ data: {
      user: { id: 'user-1', name: 'Employee to delete' },
      responsibilities: [],
      legacy_draft_candidates: [
        { id: 'draft-1', document_number: 'PO-001', action_type: 'purchase', creator_snapshot: 'Employee to delete', date: '2026-10-01' },
        { id: 'draft-2', document_number: 'AS-002', action_type: 'assign', creator_snapshot: '13800000000', date: null },
      ],
    } })

    const wrapper = mount(Organization)
    await flushPromises()
    await wrapper.find('.employee-table .row-btn.danger').trigger('click')
    await flushPromises()

    const confirm = wrapper.find('.employee-delete-modal .modal-footer .action-btn.danger')
    const checkboxes = wrapper.findAll('.legacy-draft-review input[type="checkbox"]')
    expect(checkboxes).toHaveLength(3)
    expect((confirm.element as HTMLButtonElement).disabled).toBe(true)

    await checkboxes[1].setValue(true)
    expect((confirm.element as HTMLButtonElement).disabled).toBe(true)
    await checkboxes[2].setValue(true)
    expect((confirm.element as HTMLButtonElement).disabled).toBe(false)
    await confirm.trigger('click')
    await flushPromises()

    expect(api.deleteUser).toHaveBeenCalledWith(
      'user-1',
      [],
      ['draft-1', 'draft-2'],
      ['draft-2'],
    )
    wrapper.unmount()
  })
})
