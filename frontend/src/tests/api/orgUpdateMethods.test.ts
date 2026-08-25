import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/utils/request', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: [] }),
    post: vi.fn().mockResolvedValue({ data: {} }),
    put: vi.fn().mockResolvedValue({ data: {} }),
    patch: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: {} }),
  },
  handleApiError: vi.fn(() => '请求失败'),
}))

import request from '@/utils/request'
import { updateRegion } from '@/api/regions'
import { updateBranch } from '@/api/branches'
import { updateTeam } from '@/api/teams'

describe('组织节点 update API 使用 PATCH（任命/卸任仅传单字段，PUT 会因缺必填字段 400）', () => {
  beforeEach(() => vi.clearAllMocks())

  it('updateRegion 走 PATCH', async () => {
    await updateRegion('r1', { manager: 'u1' })
    expect(request.patch).toHaveBeenCalledWith('/api/regions/r1', { manager: 'u1' })
    expect(request.put).not.toHaveBeenCalled()
  })

  it('updateBranch 走 PATCH', async () => {
    await updateBranch('b1', { manager: null })
    expect(request.patch).toHaveBeenCalledWith('/api/branches/b1', { manager: null })
    expect(request.put).not.toHaveBeenCalled()
  })

  it('updateTeam 走 PATCH', async () => {
    await updateTeam('t1', { leader: 'u2' })
    expect(request.patch).toHaveBeenCalledWith('/api/teams/t1', { leader: 'u2' })
    expect(request.put).not.toHaveBeenCalled()
  })
})
