import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { computed } from 'vue'

const api = vi.hoisted(() => ({
  getUsers: vi.fn(),
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

vi.mock('@/api/users', () => ({
  getUsers: api.getUsers,
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
  usePermission: () => ({
    canManageUsers: computed(() => false),
    canManageOrganizations: computed(() => true),
  }),
}))

import Organization from '@/views/Organization.vue'

beforeEach(() => {
  vi.resetAllMocks()
  api.getCompany.mockResolvedValue({ data: { id: 'company-1', name: 'Company' } })
  api.getRegions.mockResolvedValue({ data: [{ id: 'region-1', name: 'Region', code: 'RG' }] })
  api.getTeams.mockResolvedValue({ data: [{ id: 'team-1', name: 'Team', region: 'region-1' }] })
  api.getBranches.mockResolvedValue({
    data: [{ id: 'branch-1', name: 'Branch', code: 'BR001', team: 'team-1', status: 'active' }],
  })
  api.getUsers.mockResolvedValue({ data: [] })
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
})
